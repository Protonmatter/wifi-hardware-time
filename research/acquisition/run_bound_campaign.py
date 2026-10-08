"""Long-run action-4 TSF bound campaign. Windows/admin, explicit --execute.

One action-4 request in flight. Timing records are retained for offline
screening, not admitted live. The run stops on trace loss, lifecycle or
association change, driver change, request failure, own-loss budget or trace
cap; any stop writes a quarantine marker that this tool never clears.
"""
from __future__ import annotations

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
import ctypes as ct
import hashlib
import json
import subprocess
import threading
import time
import urllib.request
import uuid

from research.acquisition.campaign_admission import Admission, transition
from research.acquisition.campaign_gate import ReportGate
from research.clock_models.sample_screen import LISTEN_TIMEOUT_S, TIMING_KINDS

MARKER_NAME = 'bound-campaign-quarantine.json'
TRACE_CAP_BYTES = 3000 * 1024 * 1024  # loaded runs measured ~26 MiB/min
# Public 100 MB test files, tried in order. Cloudflare's speed endpoint returned 403 to these clients.
DOWNLOAD_URLS = ('https://proof.ovh.net/files/100Mb.dat', 'https://ash-speed.hetzner.com/100MB.bin')
DOWNLOAD_STALL_S = 60
USER_AGENT = 'wifi-hardware-time-load/1.0'
# ETL files hold whole buffers flushed every second, so file growth scales with buffer size
# (8 KB measured ~12 MiB/min, 256 KB ~103 MiB/min). Keep the 8 KB default size and raise the
# count to 256-2048 buffers (at most 16 MiB) so bursts under CPU load are absorbed.
TRACE_BUFFER_OPTIONS = ('-bs', '8', '-nb', '256', '2048')
IDENTITY_EVERY = 10
BEACON_EVERY_S = 10
OWN_LOSS_LIMIT = 0.01
MIN_REQUESTS_FOR_LOSS_LIMIT = 100


class BoundGate(ReportGate):
    """Keeps the live health, lifecycle and association failures; retains timing records."""

    def __init__(self) -> None:
        super().__init__()
        self.timing: list[dict] = []

    def consume(self, event: dict) -> None:
        if event.get('kind') in TIMING_KINDS:
            if self.reason:
                self._fail(self.reason)
            if type(event.get('raw_timestamp')) is not int:
                self._fail('malformed_timing_record')
            self.timing.append(event)
            return
        super().consume(event)

    def report_after(self, qpc: int) -> bool:
        return any(e['kind'] == 'report' and e['raw_timestamp'] >= qpc for e in self.timing[-16:])


def remaining_sleep(spacing_s: float, elapsed_s: float) -> float:
    return max(0.0, spacing_s - elapsed_s)


def loss_budget_exceeded(losses: int, requests: int) -> bool:
    return requests >= MIN_REQUESTS_FOR_LOSS_LIMIT and losses > OWN_LOSS_LIMIT * requests


def _save(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')


WAIT_OBJECT_0, WAIT_ABANDONED, WAIT_TIMEOUT = 0x0, 0x80, 0x102


class CampaignBusy(RuntimeError):
    """Another controller holds, or a crashed controller abandoned, this adapter's campaign lock."""


class CampaignLock:
    """Adapter-scoped named mutex held for a whole run, through cleanup and result persistence."""

    def __init__(self, adapter_guid: str, namespace: str = 'Global'):
        self.name = namespace + '\\WifiHardwareTimeBound-' + adapter_guid.strip('{}').lower()
        self.handle = None

    @staticmethod
    def _kernel():
        k = ct.WinDLL('kernel32', use_last_error=True)
        k.CreateMutexW.argtypes = [ct.c_void_p, ct.c_int, ct.c_wchar_p]
        k.CreateMutexW.restype = ct.c_void_p
        k.WaitForSingleObject.argtypes = [ct.c_void_p, ct.c_uint32]
        k.WaitForSingleObject.restype = ct.c_uint32
        k.ReleaseMutex.argtypes = [ct.c_void_p]
        k.CloseHandle.argtypes = [ct.c_void_p]
        return k

    def acquire(self) -> 'CampaignLock':
        k = self._kernel()
        handle = k.CreateMutexW(None, False, self.name)
        if not handle:
            raise ct.WinError(ct.get_last_error())
        status = k.WaitForSingleObject(handle, 0)
        if status == WAIT_OBJECT_0:
            self.handle = handle
            return self
        if status == WAIT_ABANDONED:
            k.ReleaseMutex(handle)
            k.CloseHandle(handle)
            raise CampaignBusy('A previous bound campaign ended without releasing its adapter lock; review it before rerunning')
        k.CloseHandle(handle)
        if status == WAIT_TIMEOUT:
            raise CampaignBusy('Another bound campaign is running on this adapter')
        raise OSError('Campaign lock wait failed with status ' + hex(status))

    def release(self) -> None:
        if self.handle:
            k = self._kernel()
            k.ReleaseMutex(self.handle)
            k.CloseHandle(self.handle)
            self.handle = None

    def close_handle(self) -> None:
        """Close without releasing, for a lock acquired on a thread that has since exited."""
        if self.handle:
            self._kernel().CloseHandle(self.handle)
            self.handle = None

    def __enter__(self) -> 'CampaignLock':
        return self.acquire()

    def __exit__(self, *exc) -> bool:
        self.release()
        return False


def finalize(decoder: Path, etl: Path, output: Path, live_timing: list[dict], run_fn) -> str | None:
    """Decode and verify the trace; any failure becomes a reason, never an escaping exception."""
    try:
        decoded = run_fn([str(decoder), str(etl)], timeout=600)
        output.write_text(decoded.stdout, encoding='utf-8')
        offline = [json.loads(line) for line in decoded.stdout.splitlines() if line.strip()]
        if not offline or offline[0].get('kind') != 'header':
            return 'Decoder output has no trace header'
        if offline[0].get('events_lost') or offline[0].get('buffers_lost'):
            return 'Trace reported lost events or buffers'
        live = [{k: v for k, v in e.items() if k != 'received_qpc'} for e in live_timing]
        if live != [e for e in offline if e.get('kind') in TIMING_KINDS]:
            return 'Live and offline timing records disagree'
        return None
    except BaseException as error:
        return 'Post-collection decoding failed: ' + type(error).__name__ + ': ' + str(error)


def persist_outcome(folder: Path, marker: Path, summary: dict, failure: str | None, utc_fn) -> None:
    """Write the quarantine marker first on failure, then the run result."""
    if failure:
        _save(marker, dict(created_utc=utc_fn(), run=str(folder), reason=failure))
    _save(folder / 'run-result.json', dict(summary, success=failure is None, error=failure))


def download_stalled(last_progress: float, now: float) -> bool:
    return now - last_progress > DOWNLOAD_STALL_S


def bound_workload(stop_path: Path, output: Path, max_seconds: int) -> int:
    """SHA-256 10 ms on / 10 ms off, plus a looped HTTPS download that must keep progressing."""
    start, cycles, payload = time.monotonic(), 0, bytes(65536)
    totals = dict(downloaded=0, errors=0, last_progress=start)
    stop = threading.Event()

    def download() -> None:
        attempt = 0
        while not stop.is_set():
            url = DOWNLOAD_URLS[attempt % len(DOWNLOAD_URLS)]
            try:
                request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
                with urllib.request.urlopen(request, timeout=30) as response:
                    while not stop.is_set():
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        totals['downloaded'] += len(chunk)
                        totals['last_progress'] = time.monotonic()
            except OSError:
                totals['errors'] += 1
                attempt += 1
                time.sleep(1)

    thread = threading.Thread(target=download, daemon=True)
    thread.start()
    stalled = False
    while not stop_path.exists() and time.monotonic() - start < max_seconds:
        if download_stalled(totals['last_progress'], time.monotonic()):
            stalled = True  # Fail the run rather than silently become CPU-only load.
            break
        end = time.monotonic() + 0.010
        while time.monotonic() < end:
            hashlib.sha256(payload).digest()
            cycles += 1
        time.sleep(0.010)
    stop.set()
    thread.join(timeout=35)
    wall = time.monotonic() - start
    _save(output, dict(workload='sha256-10ms-on-10ms-off plus looped HTTPS download', urls=list(DOWNLOAD_URLS),
                       wall_seconds=wall, hash_operations=cycles, downloaded_bytes=totals['downloaded'],
                       download_errors=totals['errors'], download_stalled=stalled,
                       mean_download_mbit_s=totals['downloaded'] * 8 / wall / 1e6 if wall else 0.0,
                       stop_requested=stop_path.exists()))
    if stalled:
        return 2
    return 0 if stop_path.exists() else 1


def submit(root: Path, folder: Path, number: int, index: int, frequency: int, observer, gate: BoundGate) -> dict:
    """Send one action-4 request through the existing two-phase admission protocol."""
    from research.tsf.qualcomm_protocol import QUALIFIED_SHA256
    request_path = folder / f'request-{number:05}.json'
    control = folder / f'submission-{number:05}.json'
    _save(control, dict(state='prepared', pid=None, abort_requested=False))
    admission = Admission(control, 'Local\\WifiAdmission-' + uuid.uuid4().hex, create=True)
    try:
        permitted = False
        with (folder / f'probe-{number:05}.stdout').open('w') as out, (folder / f'probe-{number:05}.stderr').open('w') as err:
            process = subprocess.Popen([sys.executable, str(root / 'research/tsf/qualcomm_probe.py'), '--if-index', str(index),
                                        '--command', 'tsf_read_value', '--tsf-action', '4', '--execute',
                                        '--output', str(request_path), '--campaign-control', str(control),
                                        '--campaign-mutex', admission.name], stdout=out, stderr=err)
            with admission.locked():
                tracking = json.loads(control.read_text())
                tracking['pid'] = process.pid
                _save(control, tracking)
            deadline = time.monotonic() + 15
            while process.poll() is None:
                observer.pump(gate)
                if not permitted:
                    with admission.locked():
                        if json.loads(control.read_text())['state'] == 'ready':
                            transition(control, 'permit')
                            permitted = True
                if time.monotonic() > deadline:
                    # Never kill a process whose overlapped IOCTL may still own buffers.
                    _save(folder / 'pending-probe.json', dict(pid=process.pid, still_running=True))
                    raise RuntimeError('Probe deadline; pending probe retained')
                time.sleep(0.005)
        if process.returncode:
            raise RuntimeError('Private probe failed')
        receipt = json.loads(request_path.read_text(encoding='utf-8'))
        if receipt['driver_sha256'] != QUALIFIED_SHA256 or receipt['qpc_frequency_hz'] != frequency:
            raise RuntimeError('Request build or clock mismatch')
        return receipt
    except BaseException:
        try:
            with admission.locked():
                transition(control, 'abort')
        except BaseException:
            pass
        raise
    finally:
        admission.close()


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--if-index', type=int)
    parser.add_argument('--condition', choices=('idle', 'load'))
    parser.add_argument('--duration-s', type=int, default=3600)
    parser.add_argument('--spacing-s', type=float, default=2.0)
    parser.add_argument('--execute', action='store_true', help='Send private requests; default is preview only')
    parser.add_argument('--workload', nargs=3, metavar=('STOP', 'OUTPUT', 'SECONDS'), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.workload is None:
        if args.if_index is None or args.condition is None:
            parser.error('--if-index and --condition are required')
        if not 60 <= args.duration_s <= 3600:
            parser.error('--duration-s must be 60 to 3600')
        if not 0.5 <= args.spacing_s <= 60:
            parser.error('--spacing-s must be 0.5 to 60')
    return args


def campaign(args: argparse.Namespace) -> int:
    from research.acquisition.bss_reader import BssReader, CacheEntryUnavailable
    from research.acquisition.run_acquisition_campaign import (PROVIDER, ROOT, Clock, Observer, TraceOwner,
                                                               identity, run, same_identity, utc)
    marker = ROOT / 'artifacts' / MARKER_NAME
    if marker.exists():
        print(f'Quarantine marker present: {marker}. Review it before any new run.', file=sys.stderr)
        return 1
    clock = Clock()
    baseline = identity(args.if_index)
    plan = dict(condition=args.condition, duration_s=args.duration_s, spacing_s=args.spacing_s, action=4,
                provider=PROVIDER, trace_cap_bytes=TRACE_CAP_BYTES, identity_every=IDENTITY_EVERY,
                beacon_every_s=BEACON_EVERY_S, own_loss_limit=OWN_LOSS_LIMIT, marker=str(marker))
    if not args.execute:
        print(json.dumps(dict(preview=True, plan=plan, adapter_status=baseline['Status'],
                              driver_version=baseline['DriverVersion']), indent=2))
        return 0
    if not ct.windll.shell32.IsUserAnAdmin():
        print('Administrator rights required for --execute.', file=sys.stderr)
        return 1
    try:
        lock = CampaignLock(baseline['InterfaceGuid']).acquire()
    except CampaignBusy as busy:
        print(f'{busy}.', file=sys.stderr)
        return 1
    try:
        # Re-check under the lock so no other controller can write or clear it meanwhile.
        if marker.exists():
            print(f'Quarantine marker present: {marker}. Review it before any new run.', file=sys.stderr)
            return 1
        return _execute(args, clock, baseline, plan, marker)
    except BaseException as error:
        _save(marker, dict(created_utc=utc(), run=None, reason=f'Controller error: {type(error).__name__}: {error}'))
        raise
    finally:
        lock.release()


def _execute(args: argparse.Namespace, clock, baseline: dict, plan: dict, marker: Path) -> int:
    from research.acquisition.bss_reader import BssReader, CacheEntryUnavailable
    from research.acquisition.run_acquisition_campaign import (PROVIDER, ROOT, Observer, TraceOwner, identity, run,
                                                               same_identity, utc)
    folder = ROOT / 'artifacts' / f'BoundCampaign-{uuid.uuid4().hex[:12]}' / args.condition
    folder.mkdir(parents=True)
    session = 'WifiBound-' + uuid.uuid4().hex[:12]
    gate, trace = BoundGate(), TraceOwner(session, folder)
    observer = worker = reader = None
    failure, receipts, beacon_count, losses, beacon_skips = None, [], 0, 0, []
    _save(folder / 'session.json', dict(SessionName=session, StartedUtc=utc(), Plan=plan))
    try:
        _save(folder / 'adapter-before.json', baseline)
        trace.start(['-p', PROVIDER, '0x2000000000000010', '0xff', '-o', str(folder / 'tsf.etl'), '-f', 'bin',
                     '-max', '3072', *TRACE_BUFFER_OPTIONS, '-rt', '-ct', 'perf', '-ft', '00:00:01', '-ets'])
        observer = Observer(session, args.if_index, folder, clock)
        observer.wait(2.5, gate)
        if not observer.ready or observer.association is None:
            raise RuntimeError('Observer readiness or association not established')
        reader = BssReader(baseline['InterfaceGuid'])
        if args.condition == 'load':
            worker = subprocess.Popen([sys.executable, __file__, '--workload', str(folder / 'workload-stop'),
                                       str(folder / 'workload.json'), str(args.duration_s + 120)],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            observer.wait(2, gate)
        end, next_beacon, number = time.monotonic() + args.duration_s, 0.0, 0
        with (folder / 'requests.jsonl').open('w', encoding='utf-8') as requests_file, \
             (folder / 'beacons.jsonl').open('w', encoding='utf-8') as beacon_file:
            while time.monotonic() < end:
                cycle = time.monotonic()
                if number % IDENTITY_EVERY == 0:
                    same_identity(identity(args.if_index), baseline)
                if worker is not None and worker.poll() is not None:
                    raise RuntimeError('Workload exited prematurely')
                if (folder / 'tsf.etl').stat().st_size > TRACE_CAP_BYTES:
                    raise RuntimeError('Trace cap reached')
                if time.monotonic() >= next_beacon:
                    try:
                        beacon = reader.read(clock.now)
                        beacon_file.write(json.dumps(dict(qpc_before=beacon.qpc_before, qpc_after=beacon.qpc_after,
                                                          ap_tsf_us=beacon.ap_tsf_us, bssid_sha256=beacon.bssid_sha256)) + '\n')
                        beacon_file.flush()
                        beacon_count += 1
                    except CacheEntryUnavailable as missing:
                        # A cache gap is not an association change; record it and skip this read.
                        beacon_skips.append(dict(qpc=clock.now(), entries=missing.count))
                    next_beacon = time.monotonic() + BEACON_EVERY_S
                number += 1
                receipt = submit(ROOT, folder, number, args.if_index, clock.frequency, observer, gate)
                receipt['sequence'] = number
                requests_file.write(json.dumps(receipt) + '\n')
                requests_file.flush()
                receipts.append(receipt)
                listen_end = time.monotonic() + LISTEN_TIMEOUT_S
                while not gate.report_after(receipt['qpc_request_before']) and time.monotonic() < listen_end:
                    observer.pump(gate)
                    time.sleep(0.005)
                if not gate.report_after(receipt['qpc_request_before']):
                    losses += 1
                if loss_budget_exceeded(losses, number):
                    raise RuntimeError('Own-loss budget exceeded')
                observer.wait(remaining_sleep(args.spacing_s, time.monotonic() - cycle), gate)
        observer.wait(2.0, gate)
    except BaseException as error:
        gate.quarantine(str(error))
        failure = str(error)
    finally:
        if reader is not None:
            reader.close()
        if worker is not None:
            (folder / 'workload-stop').touch()
            try:
                worker.wait(timeout=40)
                if worker.returncode:
                    raise RuntimeError('Workload ended without controlled stop')
            except BaseException as error:
                failure = failure or str(error)
                if worker.poll() is None:
                    worker.kill()
                    worker.wait(timeout=5)
        try:
            trace.stop()
        except BaseException as error:
            failure = failure or f'Trace cleanup: {error}'
        if observer is not None:
            try:
                observer.close(gate)
            except BaseException as error:
                failure = failure or f'Observer cleanup: {error}'
        try:
            after = identity(args.if_index)
            _save(folder / 'adapter-after.json', after)
            same_identity(after, baseline)
        except BaseException as error:
            failure = failure or f'Final identity: {error}'
    if failure is None:
        failure = finalize(ROOT / 'artifacts/decode_tsf_etl.exe', folder / 'tsf.etl', folder / 'raw-timing.jsonl',
                           gate.timing, run)
    persist_outcome(folder, marker, dict(condition=args.condition, duration_s=args.duration_s,
                                         request_count=len(receipts), own_losses_live=losses,
                                         beacon_reads=beacon_count, beacon_skips=beacon_skips,
                                         qpc_frequency_hz=clock.frequency, firmware_sampling_validated=False),
                    failure, utc)
    if failure:
        print(f'Run stopped: {failure}. Quarantine marker written: {marker}', file=sys.stderr)
        return 1
    print(json.dumps(dict(run=str(folder), requests=len(receipts), own_losses_live=losses)))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse(argv)
    if args.workload is not None:
        stop, output, seconds = args.workload
        return bound_workload(Path(stop), Path(output), int(seconds))
    return campaign(args)


if __name__ == '__main__':
    raise SystemExit(main())
