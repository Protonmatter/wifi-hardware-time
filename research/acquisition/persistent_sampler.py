"""Persistent worker control and monotonic scheduling; no hardware access on import."""
from __future__ import annotations

import contextlib
import errno
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

CONTROL_SCHEMA = 'wht/persistent-tsf-control-v1'
LEASE_S = 60.0  # Allows the existing bounded identity discovery; no future permits are queued.
MIN_GAP_FRACTION = 0.9  # an actual gap may be up to 10% shorter than the requested spacing (submission jitter)


def durable_save(path: Path, data: dict) -> None:
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, allow_nan=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextlib.contextmanager
def quarantine_locked(path: Path):
    """Cross-process marker lock, independent of the shorter-lived admission handle.

    The stable lock file is never replaced/deleted. The OS releases byte/file locks
    on process exit. All marker read/merge/replace operations hold it; admission may
    precede this lock, but no caller may acquire admission while holding this lock.
    """
    with path.with_name(path.name + '.lock').open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            def acquire():
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            def release():
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            def acquire():
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            def release():
                fcntl.flock(stream, fcntl.LOCK_UN)
        for attempt in range(101):
            try:
                acquire()
                break
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if attempt == 100:
                    raise TimeoutError('Quarantine marker lock deadline; unfinished-run guard retained') from error
                time.sleep(0.02)
        try:
            yield
        finally:
            release()


def record_quarantine(path: Path, cause: dict) -> None:
    """Durably merge distinct failure evidence; retain legacy top-level fields.

    Corrupt prior evidence is never overwritten. Marker write failure propagates;
    it cannot authorize clearing the independent unfinished-run record.
    """
    with quarantine_locked(path):
        previous = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        if type(previous) is not dict or 'causes' in cause:
            raise ValueError('Invalid quarantine evidence')
        causes = previous.get('causes', [previous] if previous else [])
        if type(causes) is not list or any(type(item) is not dict for item in causes):
            raise ValueError('Invalid quarantine causes')
        if cause not in causes:
            causes.append(cause)
        durable_save(path, dict(previous, **cause, causes=causes))


class RequestSlots:
    def __init__(self, origin: float, spacing: float):
        if not math.isfinite(origin) or not math.isfinite(spacing) or not 0.5 <= spacing <= 60:
            raise ValueError('Invalid monotonic slots')
        self.origin, self.spacing, self.next_index = origin, spacing, 0
        self.last_actual: float | None = None

    def reserve(self, now: float) -> tuple[float, int]:
        earliest = max(now, self.last_actual + self.spacing * MIN_GAP_FRACTION if self.last_actual is not None else now)
        index = max(self.next_index, math.ceil((earliest - self.origin) / self.spacing))
        skipped = index - self.next_index
        self.next_index = index + 1
        return self.origin + index * self.spacing, skipped

    def submitted(self, actual: float) -> None:
        self.last_actual = actual


class IdentityTimer:
    def __init__(self, now: float):
        self.next_check = now + 30.0

    def due(self, now: float) -> bool:
        return now >= self.next_check

    def checked(self, now: float) -> None:
        self.next_check = now + 30.0


IDENTITY_EVERY_S = 30.0
IDENTITY_MAX_AGE_S = 60.0         # a submission needs a successful check started at most this long ago
IDENTITY_CHECK_DEADLINE_S = 60.0  # one check running longer than this fails the run


def start_identity_check(fn) -> None:
    """Run one identity check off the sampling path (patched with a synchronous runner in tests)."""
    threading.Thread(target=fn, name='identity-check', daemon=True).start()


class IdentityMonitor:
    """Periodic identity checks off the sampling path; submissions are gated on a recent success.

    Construction counts as the first success, so the caller must validate identity synchronously
    immediately around construction (starting it right after construction makes the counted instant the
    check's start) and must not use the monitor if that check fails. A check's validation instant is
    taken as its start (conservative for age).
    """

    def __init__(self, check, monotonic, now_qpc, *, start=None, interval_s: float = IDENTITY_EVERY_S,
                 max_age_s: float = IDENTITY_MAX_AGE_S, deadline_s: float = IDENTITY_CHECK_DEADLINE_S):
        self.check, self.monotonic, self.now_qpc, self.start = check, monotonic, now_qpc, start
        self.interval_s, self.max_age_s, self.deadline_s = interval_s, max_age_s, deadline_s
        self.lock = threading.Lock()
        self.last_success = monotonic()
        self.next_due = self.last_success + interval_s
        self.running_since: float | None = None
        self.failure: str | None = None
        self.completed: list[dict] = []

    def maybe_start(self) -> bool:
        """Start a due check without waiting for it; False if failed, running or not yet due."""
        with self.lock:
            if self.failure is not None or self.running_since is not None or self.monotonic() < self.next_due:
                return False
            self.running_since = self.monotonic()
            self.next_due = self.running_since + self.interval_s
        try:
            (self.start or start_identity_check)(self._run)
        except BaseException as error:
            with self.lock:
                if self.failure is None:
                    self.failure = f'Identity check start failed: {type(error).__name__}: {error}'
                self.running_since = None
            return False
        return True

    def _run(self) -> None:
        started_monotonic = started_qpc = None
        error_text = None
        with self.lock:
            origin = self.running_since
        try:
            started_monotonic, started_qpc = self.monotonic(), self.now_qpc()
            self.check()
        except BaseException as error:
            error_text = f'{type(error).__name__}: {error}'
        finally:
            with self.lock:
                try:
                    if error_text is None:
                        elapsed = self.monotonic() - (origin)
                        if elapsed > self.deadline_s:
                            error_text = f'Identity check overran its {self.deadline_s:g} s deadline ({elapsed:.3f} s)'
                    if error_text is None:
                        self.last_success = started_monotonic
                    elif self.failure is None:
                        self.failure = error_text
                    self.completed.append(dict(started_qpc=started_qpc, finished_qpc=self.now_qpc(),
                                               ok=error_text is None, error=error_text))
                except BaseException as error:
                    if self.failure is None:
                        self.failure = f'{type(error).__name__}: {error}'
                finally:
                    self.running_since = None

    def gate(self) -> bool:
        """True when a submission may proceed; raises on a failed or overdue check."""
        with self.lock:
            now = self.monotonic()
            if self.failure is not None:
                raise RuntimeError(f'Identity check failed: {self.failure}')
            if self.running_since is not None and now - self.running_since > self.deadline_s:
                raise RuntimeError('Identity check overdue')
            return now - self.last_success <= self.max_age_s

    def drain_completed(self) -> list[dict]:
        with self.lock:
            records, self.completed = self.completed, []
            return records

    def wait_idle(self, wait, timeout_s: float) -> bool:
        """True once no check is running; False at timeout_s or at the running check's own deadline."""
        call_deadline = self.monotonic() + timeout_s
        while True:
            with self.lock:
                if self.running_since is None:
                    return True
                running_deadline = self.running_since + self.deadline_s
            now = self.monotonic()
            if now >= call_deadline or now > running_deadline:
                return False
            wait(0.02)


def wait_for_slot(slots: RequestSlots, end: float, timer: IdentityTimer, pulse, check_identity,
                  wait, monotonic) -> tuple[float, int]:
    """Keep owner/observer checks and identity timer alive through arbitrarily long slots."""
    skipped_total = 0
    while True:
        scheduled, skipped = slots.reserve(monotonic())
        skipped_total += skipped
        if scheduled >= end:
            return scheduled, skipped_total
        while monotonic() < scheduled:
            pulse()
            if timer.due(monotonic()):
                check_identity()
                timer.checked(monotonic())
                if monotonic() > scheduled:
                    skipped_total += 1  # This selected slot was missed during the identity check.
                    break
            wait(max(0.0, min(0.02, scheduled - monotonic())))
        else:
            pulse()
            return scheduled, skipped_total


class ControllerOwner:
    """The mutex orders revocation and submission; the process handle pins owner identity.

    This is coordination between trusted local programs, not an authentication boundary.
    Process death is observed each poll; a stalled communication lease fails within 60 s.
    """
    def __init__(self, path: Path, admission, alive, monotonic, session_id: str, pid: int):
        self.path, self.admission, self.alive, self.monotonic = path, admission, alive, monotonic
        self.session_id, self.pid = session_id, pid

    def check(self) -> dict:
        with self.admission.locked():
            return self._check_locked()

    def _check_locked(self) -> dict:
        if not self.alive():
            raise RuntimeError('Controller process disappeared')
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            raise RuntimeError('Controller communication unavailable') from error
        if (type(data) is not dict or data.get('schema') != CONTROL_SCHEMA
                or data.get('session_id') != self.session_id or data.get('controller_pid') != self.pid
                or data.get('state') not in ('starting', 'ready', 'permitted', 'submitted', 'close')
                or type(data.get('sequence')) is not int or data['sequence'] < 0):
            raise RuntimeError('Controller revoked or malformed authorization')
        heartbeat = data.get('heartbeat')
        if (type(heartbeat) not in (int, float) or not math.isfinite(heartbeat)
                or not 0 <= self.monotonic() - heartbeat <= LEASE_S):
            raise RuntimeError('Controller communication lease expired')
        return data

    @contextlib.contextmanager
    def authorize(self, sequence: int):
        with self.admission.locked():
            data = self.check()
            if data['state'] != 'permitted' or data['sequence'] != sequence:
                raise RuntimeError('Fresh request authorization required')
            data['state'] = 'submitted'
            durable_save(self.path, data)
            yield


class PersistentClient:
    """Controller side. Timeouts revoke; they NEVER kill the I/O-owning worker."""
    def __init__(self, root: Path, folder: Path, index: int, frequency: int, baseline: dict,
                 marker: Path, in_progress: Path, clock, observer, gate):
        self.root, self.folder, self.index, self.frequency = root, folder, index, frequency
        self.baseline, self.marker, self.in_progress = baseline, marker, in_progress
        self.clock, self.observer, self.gate = clock, observer, gate
        self.session_id = uuid.uuid4().hex
        self.path = folder / 'sampler-control.json'
        self.process = self.admission = None
        self.sequence = 0
        self.last_heartbeat = 0.0

    def read_snapshot(self, path: Path) -> dict:
        # Windows normal read handles do not share delete access. All protocol readers
        # close their handles under the same mutex before a worker atomic replacement.
        with self.admission.locked():
            return json.loads(path.read_text(encoding='utf-8'))

    def _control(self, state: str | None = None, sequence: int | None = None) -> None:
        with self.admission.locked():
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if state is not None:
                data['state'] = state
            if sequence is not None:
                data['sequence'] = sequence
            data['heartbeat'] = time.monotonic()
            durable_save(self.path, data)
            self.last_heartbeat = data['heartbeat']

    def pulse(self) -> None:
        self.observer.pump(self.gate)
        if self.gate.reason:
            raise RuntimeError(self.gate.reason)
        if self.process is not None and self.process.poll() is not None:
            raise RuntimeError('Persistent sampler exited')
        if time.monotonic() - self.last_heartbeat >= 1.0:
            self._control()

    def start(self) -> None:
        from research.acquisition.campaign_admission import Admission
        from research.tsf.sampler_worker import ProcessOwner
        name = 'Local\\WifiPersistent-' + self.session_id
        creation = ProcessOwner.creation_of_current()
        durable_save(self.in_progress, json.loads(self.in_progress.read_text(encoding='utf-8')))
        durable_save(self.path, dict(schema=CONTROL_SCHEMA, session_id=self.session_id,
                                    controller_pid=os.getpid(), controller_creation=creation,
                                    state='starting', sequence=0, heartbeat=time.monotonic()))
        self.admission = Admission(self.path, name, create=True)
        with (self.folder / 'sampler.stdout').open('w') as out, (self.folder / 'sampler.stderr').open('w') as err:
            self.process = subprocess.Popen([sys.executable, '-m', 'research.tsf.sampler_worker', '--execute',
                                             '--folder', str(self.folder), '--if-index', str(self.index),
                                             '--mutex', name, '--session-id', self.session_id,
                                             '--controller-pid', str(os.getpid()), '--creation', str(creation),
                                             '--marker', str(self.marker), '--in-progress', str(self.in_progress)],
                                            cwd=self.root, stdout=out, stderr=err)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            self.pulse()
            path = self.folder / 'sampler-session.json'
            if path.exists():
                session = self.read_snapshot(path)
                if session['state'] == 'READY':
                    from research.tsf.sampler_receipts import validate_session
                    validate_session(session)
                    if session['session_id'] != self.session_id or session['qpc_frequency_hz'] != self.frequency:
                        raise RuntimeError('Sampler readiness clock/session mismatch')
                    self._control('ready')
                    return
                if session.get('failed'):
                    raise RuntimeError('Sampler failed during startup')
            time.sleep(0.01)
        self.abort('Sampler readiness deadline')
        raise RuntimeError('Sampler readiness deadline; process retained')

    def submit(self, sequence: int) -> dict:
        from research.tsf.sampler_receipts import normalize
        self.pulse()
        if sequence != self.sequence + 1:
            raise RuntimeError('Nonsequential persistent request')
        self.sequence = sequence
        self._control('permitted', sequence)
        deadline = time.monotonic() + 4.0
        path = self.folder / f'sampler-request-{sequence:05}.json'
        while time.monotonic() < deadline:
            self.pulse()
            if path.exists():
                receipt = self.read_snapshot(path)
                if receipt.get('failure') or receipt.get('cancel_requested') or receipt.get('deadline_exceeded'):
                    self.abort('Persistent request failed or cancelled')
                    raise RuntimeError('Persistent request failed or cancelled; see raw sampler evidence')
                if receipt.get('completion_established'):
                    session = self.read_snapshot(self.folder / 'sampler-session.json')
                    # Session is published after request; wait for the matching terminal snapshot.
                    if session.get('request_count') == sequence and session.get('state') == 'READY':
                        _, eligible = normalize(sequence, receipt, session, self.frequency)
                        if not eligible:
                            raise RuntimeError('Persistent receipt is ineligible')
                        receipt['controller_receipt_qpc'] = self.clock.now()
                        self._control('ready')
                        return receipt
            time.sleep(0.005)
        self.abort('Persistent receipt deadline')
        raise RuntimeError('Persistent receipt deadline; worker retained for drain')

    def abort(self, reason: str) -> None:
        record_quarantine(self.marker, dict(reason=reason, sampler_session=self.session_id, pid=os.getpid()))
        if self.admission is not None:
            self._control('abort')

    def close(self, failed: bool = False) -> bool:
        from research.tsf.sampler_receipts import session_clean
        try:
            if self.process is None:
                return False
            self._control('abort' if failed else 'close')
            deadline = time.monotonic() + 4.0
            while self.process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            path = self.folder / 'sampler-session.json'
            session = self.read_snapshot(path) if path.exists() else {}
            clean = self.process.poll() == 0 and session_clean(session)
            if not clean:
                record_quarantine(self.marker, dict(reason='Sampler not cleanly closed', sampler_session=self.session_id,
                                               worker_pid=self.process.pid, still_running=self.process.poll() is None))
            return clean
        finally:
            if self.admission is not None:
                self.admission.close()
