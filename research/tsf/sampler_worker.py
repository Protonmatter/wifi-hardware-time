"""Owned persistent worker. Live startup requires the controller's explicit execute path."""
from __future__ import annotations

import argparse
import contextlib
import copy
import ctypes as ct
import json
import os
from pathlib import Path
import time

from research.acquisition.persistent_sampler import ControllerOwner, durable_save, record_quarantine
from research.tsf.tsf_sampler import Sampler, State, QUALIFIED_SHA256


class ProcessOwner:
    def __init__(self, pid: int, creation: int):
        self.k = ct.WinDLL('kernel32', use_last_error=True)
        self.k.OpenProcess.argtypes = [ct.c_uint32, ct.c_int, ct.c_uint32]
        self.k.OpenProcess.restype = ct.c_void_p
        self.k.GetProcessTimes.argtypes = [ct.c_void_p, *([ct.POINTER(ct.c_uint64)] * 4)]
        self.k.GetProcessTimes.restype = ct.c_int
        self.k.WaitForSingleObject.argtypes = [ct.c_void_p, ct.c_uint32]
        self.k.WaitForSingleObject.restype = ct.c_uint32
        self.k.CloseHandle.argtypes = [ct.c_void_p]
        self.handle = self.k.OpenProcess(0x00101000, False, pid)  # synchronize + limited query
        if not self.handle:
            raise OSError('Controller process unavailable')
        try:
            if self.created() != creation or not self.alive():
                raise RuntimeError('Controller process identity changed')
        except BaseException:
            self.close()
            raise

    def created(self) -> int:
        values = [ct.c_uint64() for _ in range(4)]
        if not self.k.GetProcessTimes(self.handle, *(ct.byref(v) for v in values)):
            raise OSError('Controller creation time unavailable')
        return values[0].value

    @staticmethod
    def creation_of_current() -> int:
        kernel = ct.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = ct.c_void_p
        kernel.GetProcessTimes.argtypes = [ct.c_void_p, *([ct.POINTER(ct.c_uint64)] * 4)]
        values = [ct.c_uint64() for _ in range(4)]
        if not kernel.GetProcessTimes(kernel.GetCurrentProcess(), *(ct.byref(v) for v in values)):
            raise OSError('Controller creation time unavailable')
        return values[0].value

    def alive(self) -> bool:
        return self.k.WaitForSingleObject(self.handle, 0) == 258

    def close(self) -> None:
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None


class Journal:
    def __init__(self, folder: Path, marker: Path, admission=None):
        self.folder, self.marker, self.admission = folder, marker, admission
        self.last_snapshot = None
        self.last_evidence_snapshot = None

    def __call__(self, snapshot: dict) -> None:
        with self.admission.locked() if self.admission is not None else contextlib.nullcontext():
            if snapshot == self.last_snapshot:
                return
            self._write(snapshot)
            self.last_snapshot = copy.deepcopy(snapshot)

    def _write(self, snapshot: dict) -> None:
        if snapshot != self.last_evidence_snapshot:
            self._write_evidence(snapshot)
            self.last_evidence_snapshot = copy.deepcopy(snapshot)
        # Retry a failed marker separately, without appending unchanged raw snapshots.
        session = snapshot['session']
        if session['failed']:
            record_quarantine(self.marker, dict(reason=session['failure'], sampler_session=session['session_id'],
                                                worker_pid=os.getpid(), drain_pending=bool(session['outstanding_operations'])))

    def _write_evidence(self, snapshot: dict) -> None:
        session, request = snapshot['session'], snapshot['request']
        with (self.folder / 'sampler-events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(snapshot, allow_nan=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        if request is not None:
            durable_save(self.folder / f"sampler-request-{request['sequence']:05}.json", request)
        if session['state'] == 'READY' and not (self.folder / 'sampler-session-start.json').exists():
            durable_save(self.folder / 'sampler-session-start.json', session)
        durable_save(self.folder / 'sampler-session.json', session)


def serve(sampler: Sampler, owner: ControllerOwner, clock) -> int:
    """Remain the strong resource owner across exceptions and disconnects until drain."""
    try:
        sampler.start()
        while sampler.state not in (State.STOPPED, State.CLOSED):
            if sampler.pending:
                sampler.step()
            else:
                command = owner.check()
                if command['state'] == 'close':
                    break
                if command['state'] == 'permitted':
                    sampler.submit(command['sequence'])
                else:
                    clock.sleep(0.02)
    except BaseException as error:
        sampler.stop(f'worker: {type(error).__name__}: {error}')
    finally:
        # This loop can live indefinitely. Never terminate the worker to satisfy a timeout.
        while sampler.pending:
            try:
                sampler.step()
            except BaseException as error:
                sampler.stop(f'drain interrupted: {type(error).__name__}')
                try:
                    clock.sleep(0.05)
                except BaseException:
                    pass
        closed = sampler.close()
    return 0 if closed and sampler.failure is None else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--if-index', type=int, required=True)
    parser.add_argument('--mutex', required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--controller-pid', type=int, required=True)
    parser.add_argument('--creation', type=int, required=True)
    parser.add_argument('--marker', type=Path, required=True)
    parser.add_argument('--in-progress', type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.execute or os.name != 'nt' or not 0 < args.if_index < 2**31:
        parser.error('Explicit Windows controller execution and valid interface required')
    from research.acquisition.campaign_admission import Admission
    from research.acquisition.run_acquisition_campaign import Clock, ROOT, identity, same_identity, run
    from research.tsf.sampler_win32 import Win32Kernel
    baseline = json.loads((args.folder / 'adapter-before.json').read_text(encoding='utf-8'))
    progress = json.loads(args.in_progress.read_text(encoding='utf-8'))
    if (args.marker.exists() or progress.get('pid') != args.controller_pid
            or progress.get('adapter_guid') != baseline['InterfaceGuid']):
        raise RuntimeError('Campaign not authorized or quarantined')
    process = ProcessOwner(args.controller_pid, args.creation)
    admission = None
    try:
        admission = Admission(args.folder / 'sampler-control.json', args.mutex)
        owner = ControllerOwner(admission.path, admission, process.alive, time.monotonic,
                                args.session_id, args.controller_pid)
        clock = Clock()
        clock.monotonic, clock.sleep = time.monotonic, time.sleep
        def validate() -> dict:
            current = identity(args.if_index)  # Full qualified hash/profile check once in this worker.
            same_identity(current, baseline)
            adapter = json.loads(run(['powershell.exe', '-NoProfile', '-File',
                                      str(ROOT / 'research/adapters/Get-QualcommAdapter.ps1'),
                                      '-InterfaceIndex', str(args.if_index)]).stdout)
            for field in ('ifIndex', 'Status', 'DriverFileName', 'DriverVersion', 'DriverPath', 'ServiceState'):
                if adapter[field] != current[field]:
                    raise RuntimeError('Adapter changed during startup')
            return dict(identity_validated=True, driver_sha256=QUALIFIED_SHA256,
                        interface_index=current['ifIndex'], adapter_guid=current['InterfaceGuid'],
                        mac_hex=adapter['MacAddress'].replace('-', '').replace(':', ''))
        sampler = Sampler(Win32Kernel(live=True), clock, owner, Journal(args.folder, args.marker, admission),
                          validate, session_id=args.session_id)
        return serve(sampler, owner, clock)
    finally:
        if admission is not None:
            admission.close()
        process.close()


if __name__ == '__main__':
    raise SystemExit(main())
