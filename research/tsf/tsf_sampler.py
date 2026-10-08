"""Single-session action-4 sampler. Importing this module never loads a device API.

The worker owns this object until every operation is terminal. step() is bounded;
close() returns False while ownership must be retained. Neither is a kill deadline.
Mechanics reference: qualcomm_probe.py at c620f47c94e4691347c6a905860fe435be1aa575.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol

from research.tsf.qualcomm_protocol import QUALIFIED_SHA256, build_request

REQUEST_SCHEMA = 'wht/persistent-tsf-request-v1'
SESSION_SCHEMA = 'wht/persistent-tsf-session-v1'
DEADLINE_S = 2.0
POLL_MS = 50


class State(str, Enum):
    NEW = 'NEW'
    READY = 'READY'
    IN_FLIGHT = 'IN_FLIGHT'
    COMPLETED_SUCCESS = 'COMPLETED_SUCCESS'
    COMPLETED_ERROR = 'COMPLETED_ERROR'
    DEADLINE_EXCEEDED = 'DEADLINE_EXCEEDED'
    CANCEL_REQUESTED = 'CANCEL_REQUESTED'
    QUARANTINED_DRAIN_PENDING = 'QUARANTINED_DRAIN_PENDING'
    STOPPED = 'STOPPED'
    CLOSED = 'CLOSED'


@dataclass(frozen=True)
class IoResult:
    success: bool
    error: int
    returned: int
    response: bytes


@dataclass(frozen=True)
class PollResult:
    wait_status: int
    result: IoResult | None


class Clock(Protocol):
    frequency: int
    def now(self) -> int: ...
    def monotonic(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class Kernel(Protocol):
    def open(self) -> None: ...
    def allocate(self, payload: bytes) -> object: ...
    def submit(self, operation: object) -> IoResult: ...
    def poll(self, operation: object, timeout_ms: int) -> PollResult: ...
    def cancel(self, operation: object) -> tuple[bool, int]: ...
    def release(self, operation: object) -> bool: ...
    def close(self) -> bool: ...


class Sampler:
    """Injected state machine; the worker, not a finalizer, owns its lifetime."""

    def __init__(self, kernel: Kernel, clock: Clock, owner, sink: Callable[[dict], None],
                 validate_identity: Callable[[], dict], *, session_id: str):
        self.kernel, self.clock, self.owner, self.sink = kernel, clock, owner, sink
        self.validate_identity, self.session_id = validate_identity, session_id
        self.state = State.NEW
        self.operation: object | None = None
        self.pending = False
        self.failure: str | None = None
        self.receipt: dict | None = None
        self.sequence = 0
        self.deadline = 0.0
        self.close_attempted = False
        self.session = dict(schema=SESSION_SCHEMA, session_id=session_id, state='NEW',
                            identity_validated=False, handle_opened=False, handle_closed=False,
                            handle_close_attempted=False, outstanding_operations=0, failed=False,
                            qpc_frequency_hz=clock.frequency, clock='QPC', request_count=0)

    def _emit(self) -> None:
        self.session.update(state=self.state.value, failed=self.failure is not None, failure=self.failure,
                            outstanding_operations=int(self.pending), request_count=self.sequence)
        self.sink(copy.deepcopy(dict(session=self.session, request=self.receipt)))

    def start(self) -> None:
        if self.state != State.NEW:
            raise RuntimeError('Session already started')
        self.owner.check()
        identity = self.validate_identity()
        if (identity.get('identity_validated') is not True or identity.get('driver_sha256') != QUALIFIED_SHA256
                or type(self.clock.frequency) is not int or self.clock.frequency <= 0):
            raise ValueError('Qualified identity and QPC frequency required')
        self.payload = build_request('tsf_read_value', bytes.fromhex(identity['mac_hex']), tsf_action=4)
        self.session.update(identity=identity, identity_validated=True, started_qpc=self.clock.now())
        self._emit()  # Persist identity before opening anything.
        self.owner.check()
        self.kernel.open()
        self.session['handle_opened'] = True
        self.state = State.READY
        try:
            self._emit()
        except BaseException:
            self.stop('session evidence persistence failed')
            self.close()
            raise

    def _fail(self, reason: str) -> None:
        self.failure = self.failure or reason
        if self.receipt is not None:
            self.receipt.update(success=False, failure=self.failure)

    def submit(self, sequence: int) -> None:
        if self.state != State.READY or self.failure or type(sequence) is not int or sequence != self.sequence + 1:
            raise RuntimeError('Session not ready for next sequential authorization')
        self.sequence = sequence
        self.receipt = dict(schema=REQUEST_SCHEMA, session_id=self.session_id, sequence=sequence,
                            command='tsf_read_value', firmware_action=4, ioctl='0x00220182',
                            input_bytes=128, output_capacity=100, driver_sha256=QUALIFIED_SHA256,
                            interface_index=self.session['identity']['interface_index'],
                            clock='QPC', qpc_frequency_hz=self.clock.frequency,
                            qpc_request_before=None, qpc_request_completed=None,
                            initial_success=None, initial_error=None, wait_result=None,
                            deadline_exceeded=False, cancel_requested=False, cancel_accepted=None,
                            cancel_error=None, completion_established=False, terminal_success=None,
                            terminal_error=None, returned_bytes=None, response_hex=None, success=False)
        try:
            self._emit()
            self.operation = self.kernel.allocate(self.payload)
            with self.owner.authorize(sequence):
                self.owner.check()  # Recheck at the actual submission boundary under the authorization lock.
                self.receipt['submission_monotonic'] = self.clock.monotonic()
                self.deadline = self.receipt['submission_monotonic'] + DEADLINE_S
                self.receipt['qpc_request_before'] = self.clock.now()
                self.pending = True  # Exceptions after entering the native call are ambiguous.
                self.state = State.IN_FLIGHT
                result = self.kernel.submit(self.operation)
            self.receipt.update(initial_success=result.success, initial_error=result.error)
            if result.success or result.error != 997:
                self._terminal(result)
            self._emit()
        except BaseException as error:
            self.stop(f'submission: {type(error).__name__}: {error}')

    def _terminal(self, result: IoResult) -> None:
        self.pending = False  # Completion proven before fallible QPC or evidence operations.
        self.receipt.update(completion_established=True, terminal_success=result.success,
                            terminal_error=result.error, returned_bytes=result.returned)
        if self.clock.monotonic() >= self.deadline:
            self.receipt['deadline_exceeded'] = True
            self._fail('request deadline exceeded')
        try:
            self.receipt['qpc_request_completed'] = self.clock.now()
            if not 0 <= result.returned <= 100 or (result.success and len(result.response) != result.returned):
                raise ValueError('Driver output exceeds capacity or has inconsistent length')
            self.receipt['response_hex'] = result.response.hex() if result.success else ''
            if not result.success:
                self._fail('terminal I/O error')
        except BaseException as error:
            self._fail(f'terminal evidence: {error}')
        self.state = State.COMPLETED_ERROR if self.failure else State.COMPLETED_SUCCESS
        self.receipt['success'] = self.failure is None and result.success
        self._release_operation()
        self.state = State.STOPPED if self.failure else State.READY

    def _release_operation(self) -> None:
        if self.operation is not None and not self.pending:
            try:
                if not self.kernel.release(self.operation):
                    self._fail('event close failed')
                else:
                    self.operation = None
            except BaseException as error:
                self._fail(f'event close: {error}')

    def stop(self, reason: str) -> None:
        self._fail(reason)
        if self.pending:
            if not self.receipt['cancel_requested']:
                self.state = State.CANCEL_REQUESTED
                self.receipt['cancel_requested'] = True
                try:
                    accepted, error = self.kernel.cancel(self.operation)
                    self.receipt.update(cancel_accepted=accepted, cancel_error=error)
                except BaseException as error:
                    self.receipt['cancel_exception'] = type(error).__name__ + ': ' + str(error)
            self.state = State.QUARANTINED_DRAIN_PENDING
        elif self.state != State.CLOSED:
            self._release_operation()
            self.state = State.STOPPED
        try:
            self._emit()
        except BaseException:
            # The worker retries persistence and keeps the pre-existing unfinished-run record.
            self.session['evidence_write_failed'] = True

    def step(self) -> None:
        if not self.pending:
            return
        started = self.clock.monotonic()
        try:
            self.owner.check()
        except BaseException as error:
            self.stop(f'ownership lost: {error}')
        if not self.receipt['deadline_exceeded'] and self.clock.monotonic() >= self.deadline:
            self.receipt['deadline_exceeded'] = True
            self.state = State.DEADLINE_EXCEEDED
            self.stop('request deadline exceeded')
        try:
            polled = self.kernel.poll(self.operation, POLL_MS)
            self.receipt['wait_result'] = polled.wait_status
            if polled.wait_status not in (0, 258):
                self.stop('unexpected or failed wait')
            elif polled.result is not None:
                self._terminal(polled.result)
            self._emit()
        except BaseException as error:
            self.stop(f'completion polling: {type(error).__name__}: {error}')
        # Faults or a stale signaled event must not turn repeated finite polls into a spin.
        remaining = POLL_MS / 1000 - (self.clock.monotonic() - started)
        if self.pending and remaining > 0:
            self.clock.sleep(remaining)

    def close(self) -> bool:
        if self.pending:
            self.stop('close requested while I/O unresolved')
            return False
        if self.close_attempted:
            return self.session['handle_closed'] is True
        self._release_operation()
        self.close_attempted = True
        self.session['handle_close_attempted'] = True
        if self.session['handle_opened']:
            try:
                self.session['handle_closed'] = bool(self.kernel.close())
            except BaseException as error:
                self._fail(f'device close: {error}')
            if not self.session['handle_closed']:
                self._fail('device close failed')
        self.state = State.CLOSED if self.session['handle_closed'] else State.STOPPED
        try:
            self.session['ended_qpc'] = self.clock.now()
            self._emit()
        except BaseException as error:
            self._fail(f'final evidence: {error}')
            return False
        return self.session['handle_closed'] is True and self.operation is None
