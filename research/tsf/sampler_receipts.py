"""Strict persistent receipts. Normalization never fabricates legacy handle closure."""
from research.tsf.qualcomm_protocol import QUALIFIED_SHA256
from research.tsf.tsf_sampler import REQUEST_SCHEMA, SESSION_SCHEMA


def _integer(record: dict, field: str, minimum: int = 0) -> int:
    value = record.get(field)
    if type(value) is not int or value < minimum:
        raise ValueError(f'Invalid integer {field}')
    return value


def _boolean(record: dict, field: str) -> bool:
    value = record.get(field)
    if type(value) is not bool:
        raise ValueError(f'Invalid boolean {field}')
    return value


def validate_session(session: dict) -> None:
    if type(session) is not dict or session.get('schema') != SESSION_SCHEMA:
        raise ValueError('Missing or unknown persistent session schema')
    if not isinstance(session.get('session_id'), str) or not session['session_id'] or session.get('clock') != 'QPC':
        raise ValueError('Session identity/clock missing')
    for field in ('identity_validated', 'handle_opened', 'handle_closed', 'handle_close_attempted', 'failed'):
        _boolean(session, field)
    if not session['failed'] and (session.get('failure') is not None or session.get('evidence_write_failed')):
        raise ValueError('Contradictory session failure evidence')
    if not session['identity_validated'] or not session['handle_opened']:
        raise ValueError('Unvalidated or unopened session')
    _integer(session, 'qpc_frequency_hz', 1)
    _integer(session, 'started_qpc')
    _integer(session, 'request_count')
    if _integer(session, 'outstanding_operations') != 0 or session.get('state') not in ('READY', 'STOPPED', 'CLOSED'):
        raise ValueError('Unresolved session lifecycle')
    identity = session.get('identity')
    if (type(identity) is not dict or identity.get('driver_sha256') != QUALIFIED_SHA256
            or identity.get('identity_validated') is not True or not identity.get('adapter_guid')):
        raise ValueError('Session lacks validated adapter provenance')
    _integer(identity, 'interface_index', 1)
    if session['state'] == 'CLOSED':
        if not session['handle_closed'] or not session['handle_close_attempted']:
            raise ValueError('Unverified session closure')
        if _integer(session, 'ended_qpc') < session['started_qpc']:
            raise ValueError('Reversed session lifetime')
    elif session['handle_closed']:
        raise ValueError('Contradictory handle lifecycle')


def normalize(sequence: int, receipt: dict, session: dict, qpc_hz: int | None = None) -> tuple[int, bool]:
    validate_session(session)
    if receipt.get('schema') != REQUEST_SCHEMA or 'handle_closed' in receipt:
        raise ValueError('Unknown request schema or fabricated per-request closure')
    if receipt.get('session_id') != session['session_id'] or receipt.get('clock') != 'QPC':
        raise ValueError('Request/session linkage mismatch')
    if _integer(receipt, 'sequence', 1) != sequence or sequence > session['request_count']:
        raise ValueError('Request sequence mismatch')
    frequency = _integer(receipt, 'qpc_frequency_hz', 1)
    if frequency != session['qpc_frequency_hz'] or (qpc_hz is not None and frequency != qpc_hz):
        raise ValueError('Request/session/trace QPC mismatch')
    lower, upper = _integer(receipt, 'qpc_request_before'), _integer(receipt, 'qpc_request_completed')
    if lower < session['started_qpc'] or upper < lower or (session['state'] == 'CLOSED' and upper > session['ended_qpc']):
        raise ValueError('Request outside session lifetime')
    for field, expected in dict(command='tsf_read_value', firmware_action=4, ioctl='0x00220182', input_bytes=128,
                                output_capacity=100, driver_sha256=QUALIFIED_SHA256,
                                interface_index=session['identity']['interface_index']).items():
        if receipt.get(field) != expected or type(receipt.get(field)) is not type(expected):
            raise ValueError(f'Request provenance mismatch: {field}')
    for field in ('success', 'initial_success', 'terminal_success', 'completion_established',
                  'deadline_exceeded', 'cancel_requested'):
        _boolean(receipt, field)
    if not receipt['completion_established']:
        raise ValueError('Request completion unresolved')
    if 'event_close_attempted' in receipt or 'event_closed' in receipt:
        attempted = _boolean(receipt, 'event_close_attempted')
        closed = _boolean(receipt, 'event_closed')
        if (closed and not attempted) or (receipt['success'] and not closed):
            raise ValueError('Contradictory event closure evidence')
    initial_error = _integer(receipt, 'initial_error')
    terminal_error = _integer(receipt, 'terminal_error')
    if receipt['initial_success'] != (initial_error == 0) or receipt['terminal_success'] != (terminal_error == 0):
        raise ValueError('Contradictory I/O result')
    if initial_error != 997 and (receipt['initial_success'] != receipt['terminal_success'] or initial_error != terminal_error):
        raise ValueError('A nonpending initial result cannot change at terminal completion')
    for field in ('wait_result', 'cancel_accepted', 'cancel_error'):
        if field not in receipt:
            raise ValueError(f'Missing {field}')
    if receipt['wait_result'] is not None:
        _integer(receipt, 'wait_result')
    if initial_error == 997 and receipt['wait_result'] not in (0, 258):
        raise ValueError('Pending request without a resolved wait')
    if receipt['cancel_requested']:
        _boolean(receipt, 'cancel_accepted')
        _integer(receipt, 'cancel_error')
        if receipt['cancel_accepted'] != (receipt['cancel_error'] == 0):
            raise ValueError('Contradictory cancellation result')
    elif receipt['cancel_accepted'] is not None or receipt['cancel_error'] is not None:
        raise ValueError('Unrequested cancellation result')
    returned = _integer(receipt, 'returned_bytes')
    try:
        raw = bytes.fromhex(receipt['response_hex'])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Missing or corrupt response representation') from error
    if returned > 100 or len(raw) != (returned if receipt['terminal_success'] else 0):
        raise ValueError('Invalid returned extent')
    succeeded = (receipt['success'] and receipt['terminal_success'] and not receipt['cancel_requested']
                 and not receipt['deadline_exceeded'])
    if receipt['success'] and not succeeded:
        raise ValueError('Contradictory successful request')
    return lower, succeeded


def session_clean(session: dict) -> bool:
    try:
        validate_session(session)
        return (session['state'] == 'CLOSED' and session['failed'] is False
                and not session.get('evidence_write_failed'))
    except (ValueError, TypeError, KeyError):
        return False
