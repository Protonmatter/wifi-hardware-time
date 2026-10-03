"""Offline NDIS status correlation and documented read-only topology snapshots.

Snapshots and full correlation outputs contain private interface identities and
possibly kernel request pointers. Keep them local. Snapshot calls only IP Helper
enumeration and host-clock APIs. It does not query an OID or create an ETW session.
Exit 0 means evidence was processed, 1 means rejection/I/O failure, 2 means usage.
No classification establishes hardware capability or complete request lifecycle.
"""
from __future__ import annotations

import argparse
from collections import deque
import copy
import ctypes as c
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
import uuid

NDIS_PROVIDER = 'cdead503-17f5-4a3e-b7ae-df8cc2902eb9'
NDIS_BUILD = 'd90b185d403966577fe5f8bed708a4b09c8da68730690e89f9ad41304792f64a'
MAX_ROWS, MAX_EDGES, MAX_EVENTS = 4096, 16384, 65536
MAX_FILE_BYTES = 32 * 1024 * 1024
U32, U64 = (1 << 32) - 1, (1 << 64) - 1
QPC_MAX = (1 << 63) - 1
OPERATIONS = {'supported': '0x00a00001', 'active': '0x00a00002', 'cross': '0x00a00003'}


def _keys(value: Any, names: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(names.split()):
        raise ValueError('Missing or unsupported evidence fields')
    return value


def _integer(value: Any, maximum: int = U32, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('Invalid integer field')
    return value


def _decimal(value: Any, maximum: int = U64, minimum: int = 0) -> int:
    if type(value) is not str or not re.fullmatch(r'0|[1-9][0-9]{0,19}', value):
        raise ValueError('Expected canonical decimal string')
    return _integer(int(value), maximum, minimum)


def _hex(value: Any, digits: int = 8) -> str:
    if type(value) is not str or not re.fullmatch(r'0x[0-9a-f]{' + str(digits) + '}', value):
        raise ValueError('Expected fixed-width lowercase hexadecimal field')
    return value


def _guid(value: Any) -> str:
    if type(value) is not str or not re.fullmatch(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', value):
        raise ValueError('Expected canonical GUID')
    return value


def _activity(value: Any) -> str | None:
    if value is None:
        return None
    result = _guid(value)
    return None if result == str(uuid.UUID(int=0)) else result


def _utc(value: Any) -> datetime:
    if type(value) is not str or len(value) > 40:
        raise ValueError('Invalid UTC timestamp')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError('Invalid UTC timestamp') from None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError('UTC timestamp required')
    return parsed


def validate_snapshot(snapshot: Any) -> tuple[dict[int, dict[str, Any]], set[tuple[int, int]]]:
    """Validate the bounded graph, including uniqueness and all directed cycles."""
    s = _keys(snapshot, 'schema clock qpc_frequency_hz qpc_before qpc_after utc_before utc_after observation_atomic target rows edges unresolved_indices')
    if s['schema'] != 'ndis-topology/v1' or s['clock'] != 'qpc' or s['observation_atomic'] is not False:
        raise ValueError('Unsupported topology contract or atomicity claim')
    _decimal(s['qpc_frequency_hz'], QPC_MAX, 1)
    if _decimal(s['qpc_before'], QPC_MAX) > _decimal(s['qpc_after'], QPC_MAX) or _utc(s['utc_before']) > _utc(s['utc_after']):
        raise ValueError('Reversed topology observation window')
    if type(s['rows']) is not list or not 1 <= len(s['rows']) <= MAX_ROWS:
        raise ValueError('Invalid interface-table size')
    rows: dict[int, dict[str, Any]] = {}
    guids: set[str] = set()
    luids: set[int] = set()
    for raw in s['rows']:
        row = _keys(raw, 'index guid luid flags type physical oper_status admin_status media_connect_state')
        index = _integer(row['index'], minimum=1)
        guid, luid = _guid(row['guid']), _decimal(row['luid'], minimum=1)
        if index in rows or guid in guids or luid in luids:
            raise ValueError('Ambiguous interface identity')
        _integer(row['flags'], 255)
        for field in ('type', 'physical', 'oper_status', 'admin_status', 'media_connect_state'):
            _integer(row[field])
        rows[index] = row
        guids.add(guid)
        luids.add(luid)
    target = _keys(s['target'], 'index guid luid')
    index = _integer(target['index'], minimum=1)
    _guid(target['guid'])
    _decimal(target['luid'], minimum=1)
    if index not in rows or any(target[k] != rows[index][k] for k in target):
        raise ValueError('Target identity tuple does not match raw table')
    if type(s['edges']) is not list or len(s['edges']) > MAX_EDGES:
        raise ValueError('Invalid stack-table size')
    edges: set[tuple[int, int]] = set()
    outgoing: dict[int, list[int]] = {i: [] for i in rows}
    degree = dict.fromkeys(rows, 0)
    for raw in s['edges']:
        edge = _keys(raw, 'upper lower')
        upper, lower = _integer(edge['upper']), _integer(edge['lower'])
        if (upper, lower) in edges or upper == lower:
            raise ValueError('Duplicate or self-referential stack edge')
        edges.add((upper, lower))
        # Index zero is the documented stack boundary, not an interface vertex.
        for vertex in (upper, lower):
            if vertex:
                outgoing.setdefault(vertex, [])
                degree.setdefault(vertex, 0)
        if upper and lower:
            outgoing[upper].append(lower)
            degree[lower] += 1
    unknown = sorted({i for pair in edges for i in pair if i and i not in rows})
    if type(s['unresolved_indices']) is not list or any(type(i) is not int for i in s['unresolved_indices']) or s['unresolved_indices'] != unknown:
        raise ValueError('Unresolved stack-vertex inventory differs from raw graph')
    if len(degree) > MAX_ROWS:
        raise ValueError('Stack graph exceeds vertex limit')
    queue = deque(i for i, count in degree.items() if count == 0)
    seen = 0
    while queue:
        current = queue.popleft()
        seen += 1
        for lower in outgoing[current]:
            degree[lower] -= 1
            if degree[lower] == 0:
                queue.append(lower)
    if seen != len(degree):
        raise ValueError('Cycle in interface stack')
    return rows, edges


def _ancestors(target: int, edges: set[tuple[int, int]]) -> dict[int, int]:
    reverse: dict[int, list[int]] = {}
    for upper, lower in sorted(edges):
        if upper and lower:
            reverse.setdefault(lower, []).append(upper)
    hops = {target: 0}
    queue = deque([target])
    while queue:
        lower = queue.popleft()
        for upper in reverse.get(lower, []):
            if upper not in hops:
                hops[upper] = hops[lower] + 1
                queue.append(upper)
    return hops


def _validate_health(health: Any, frequency: int) -> None:
    h = _keys(health, 'schema etl_sha256 ndis_sha256 finalized file_limit_reached controller header decode')
    if h['schema'] != 'ndis-trace-health/v1' or h['finalized'] is not True or h['file_limit_reached'] is not False:
        raise ValueError('Unfinalized, size-limited or unsupported trace')
    for field in ('etl_sha256', 'ndis_sha256'):
        if type(h[field]) is not str or not re.fullmatch('[0-9a-f]{64}', h[field]):
            raise ValueError('Invalid trace provenance digest')
    controller = _keys(h['controller'], 'query_status stop_status events_lost log_buffers_lost realtime_buffers_lost buffers_written')
    header = _keys(h['header'], 'events_lost buffers_lost end_time_100ns clock_type perf_frequency_hz pointer_size buffers_written')
    decode = _keys(h['decode'], 'process_status close_status')
    for fields, names in [(controller, 'query_status stop_status events_lost log_buffers_lost realtime_buffers_lost'),
                          (header, 'events_lost buffers_lost'), (decode, 'process_status close_status')]:
        if any(_integer(fields[name]) != 0 for name in names.split()):
            raise ValueError('Trace loss or failed controller/decoder operation')
    if _integer(header['clock_type']) != 1 or _integer(header['pointer_size']) != 8:
        raise ValueError('Unsupported trace clock or pointer width')
    if _decimal(header['perf_frequency_hz'], QPC_MAX, 1) != frequency:
        raise ValueError('Trace frequency differs from query')
    _decimal(header['end_time_100ns'], minimum=1)
    for fields in (controller, header):
        _integer(fields['buffers_written'], minimum=1)


def _event(event: Any) -> dict[str, Any]:
    e = _keys(event, 'provider id version activity_id pid tid qpc data')
    if _guid(e['provider']) != NDIS_PROVIDER or _integer(e['version']) != 0:
        raise ValueError('Unsupported event provider/version')
    event_id = _integer(e['id'])
    fields = {
        10101: 'Request CompleteRequest Status Oid',
        10111: 'RequestType Status Location',
        10112: 'RequestType Status Location',
        10018: 'Request Status Location',
        10102: 'Request Status Location',
        10052: 'Oid Status Location',
    }
    if event_id not in fields:
        raise ValueError('Unsupported event ID')
    data = _keys(e['data'], 'IfGuid IfIndex NetLuid ' + fields[event_id])
    _guid(data['IfGuid'])
    _decimal(data['IfIndex'], U32, 1)
    _decimal(data['NetLuid'], minimum=1)
    _hex(data['Status'])
    if 'Oid' in data:
        _hex(data['Oid'])
    if 'RequestType' in data:
        _hex(data['RequestType'])
    if 'Request' in data and int(_hex(data['Request'], 16), 16) == 0:
        raise ValueError('Null request pointer')
    if 'Location' in data:
        _decimal(data['Location'], U32)
    if 'CompleteRequest' in data and type(data['CompleteRequest']) is not bool:
        raise ValueError('Invalid CompleteRequest Boolean')
    _activity(e['activity_id'])
    _integer(e['pid'])
    _integer(e['tid'])
    _decimal(e['qpc'], QPC_MAX)
    return e


def correlate(snapshot_before: Any, snapshot_after: Any, query: Any,
              events: Any, health: Any) -> dict[str, Any]:
    """Classify one public query conservatively; never infer complete lifecycle.

    Validated equal endpoint snapshots bound an observation interval but cannot
    rule out transient changes between them. Activity correlation is stronger
    than proximity, but neither class identifies the original rejecting layer.
    Invalid/incomplete evidence produces an explicit rejected result.
    """
    result: dict[str, Any] = dict(classification='rejected', reasons=[], matches=[],
        raw_statuses=[], request_lifecycle_validated=False, hardware_capability_validated=False,
        topology_continuity_validated=False, originating_rejecting_layer_validated=False)
    try:
        rows, edges = validate_snapshot(snapshot_before)
        rows_after, edges_after = validate_snapshot(snapshot_after)
        q = _keys(query, 'schema operation oid pid tid qpc_before qpc_after qpc_frequency_hz return_code activity_id interface_index interface_luid')
        if q['schema'] != 'ndis-query/v1' or type(q['operation']) is not str or OPERATIONS.get(q['operation']) != _hex(q['oid']):
            raise ValueError('Operation/OID mismatch')
        _integer(q['pid'], minimum=1)
        _integer(q['tid'], minimum=1)
        _integer(q['return_code'])
        activity = _activity(q['activity_id'])
        begin, end = _decimal(q['qpc_before'], QPC_MAX), _decimal(q['qpc_after'], QPC_MAX)
        frequency = _decimal(q['qpc_frequency_hz'], QPC_MAX, 1)
        _validate_health(health, frequency)
        target = snapshot_before['target']
        if snapshot_after['target'] != target or _integer(q['interface_index'], minimum=1) != target['index'] or _decimal(q['interface_luid'], minimum=1) != int(target['luid']):
            raise ValueError('Query/target identity mismatch')
        if not int(snapshot_before['qpc_after']) <= begin <= end <= int(snapshot_after['qpc_before']):
            raise ValueError('Topology snapshots do not bracket query')
        if any(int(s['qpc_frequency_hz']) != frequency for s in (snapshot_before, snapshot_after)):
            raise ValueError('Topology/query clocks differ')
        if _utc(snapshot_before['utc_after']) > _utc(snapshot_after['utc_before']):
            raise ValueError('Topology UTC order inconsistent')
        hops = _ancestors(target['index'], edges)
        after_hops = _ancestors(target['index'], edges_after)
        if any(i not in rows for i in hops) or any(i not in rows_after for i in after_hops):
            raise ValueError('Target-stack path contains an unresolved interface')
        if set(hops) != set(after_hops) or any(rows[i] != rows_after[i] for i in hops):
            raise ValueError('Target-stack identity/state changed between snapshots')
        relevant_edges = {(u, v) for u, v in edges if u in hops and v in hops}
        if relevant_edges != {(u, v) for u, v in edges_after if u in after_hops and v in after_hops}:
            raise ValueError('Target-stack edges changed between snapshots')
        if type(events) is not list or len(events) > MAX_EVENTS:
            raise ValueError('Invalid event collection size')
        previous = -1
        primaries = 0
        matches: list[dict[str, Any]] = []
        for position, raw in enumerate(events):
            e = _event(raw)
            tick = int(e['qpc'])
            if tick < previous:
                raise ValueError('Events are not ordered by raw QPC')
            previous = tick
            if not begin <= tick <= end:
                continue
            data = e['data']
            interpretation = 'named_Oid'
            oid = data.get('Oid')
            if 'RequestType' in data:
                if health['ndis_sha256'] != NDIS_BUILD or e['id'] != 10111 or data['Location'] != '65537':
                    raise ValueError('RequestType OID interpretation lacks exact producer evidence')
                oid, interpretation = data['RequestType'], 'RequestType_inferred_exact_build'
            if oid != q['oid']:
                continue  # Pointer-only events cannot independently bind this query.
            index = int(data['IfIndex'])
            if index not in rows or rows[index]['guid'] != data['IfGuid'] or rows[index]['luid'] != data['NetLuid']:
                raise ValueError('Event interface identity tuple differs from topology')
            if index not in hops:
                continue
            if e['id'] == 10101:
                if not data['CompleteRequest']:
                    continue
                primaries += 1
            matches.append(dict(event_index=position, id=e['id'], version=e['version'],
                data=copy.deepcopy(data), oid_interpretation=interpretation,
                downward_hops=hops[index], activity_match=bool(activity and activity == _activity(e['activity_id'])),
                activity_scope='interface' if _activity(e['activity_id']) == data['IfGuid'] else 'unknown'))
        if primaries > 1:
            raise ValueError('Ambiguous completed OID requests in query window')
        statuses = sorted({m['data']['Status'] for m in matches})
        if len(statuses) > 1:
            raise ValueError('Conflicting raw statuses in query window')
        result.update(matches=matches, raw_statuses=statuses)
        if not matches:
            result.update(classification='inconclusive', reasons=['No matching completed OID status event'])
        elif primaries == 1 and all(m['activity_match'] and m['activity_scope'] != 'interface' for m in matches) and all(m['id'] == 10101 for m in matches):
            result.update(classification='activity_stack_correlated', reasons=['Unique completed OID event shares ActivityID and stable endpoint stack'])
        else:
            result.update(classification='temporal_stack_candidate', reasons=['Temporal/stack association only; request binding is not established'])
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        result.update(classification='rejected', reasons=[str(error)], matches=[], raw_statuses=[])
    return result


class _Row(c.Structure):
    _fields_ = [('luid', c.c_uint64), ('index', c.c_uint32), ('guid', c.c_ubyte * 16),
                ('alias', c.c_wchar * 257), ('description', c.c_wchar * 257),
                ('addrlen', c.c_uint32), ('addr', c.c_ubyte * 32), ('perm', c.c_ubyte * 32)]
    _fields_ += [(name, c.c_uint32) for name in ('mtu', 'type', 'tunnel', 'media', 'physical', 'access', 'direction')]
    _fields_ += [('flags', c.c_ubyte)] + [(name, c.c_uint32) for name in ('oper', 'admin', 'connect')]
    _fields_ += [('netguid', c.c_ubyte * 16), ('connection', c.c_uint32)]
    _fields_ += [('counter_' + str(i), c.c_uint64) for i in range(20)]


class _Table(c.Structure):
    _fields_ = [('count', c.c_uint32), ('rows', _Row * 1)]


class _StackRow(c.Structure):
    _fields_ = [('upper', c.c_uint32), ('lower', c.c_uint32)]


class _StackTable(c.Structure):
    _fields_ = [('count', c.c_uint32), ('rows', _StackRow * 1)]


def capture_snapshot(interface_index: int, expected_guid: str) -> dict[str, Any]:
    """Enumerate raw interface/stack tables once, with native QPC/UTC brackets.

    Requires 64-bit Windows with the SDK-checked structure layout. Tables are
    sequential observations, not an atomic graph. All returned memory is freed.
    """
    _integer(interface_index, minimum=1)
    _guid(expected_guid)
    if os.name != 'nt':
        raise ValueError('Snapshot requires Windows; offline correlation is portable')
    if (c.sizeof(c.c_void_p), c.sizeof(c.c_wchar), c.sizeof(_Row), _Table.rows.offset,
            c.sizeof(_StackRow), _StackTable.rows.offset) != (8, 2, 1352, 8, 8, 4):
        raise ValueError('Unsupported IP Helper structure layout')
    kernel = c.WinDLL('kernel32', use_last_error=True)
    for name in ('QueryPerformanceCounter', 'QueryPerformanceFrequency'):
        function = getattr(kernel, name)
        function.argtypes, function.restype = [c.POINTER(c.c_int64)], c.c_int

    def clock(name: str) -> int:
        value = c.c_int64()
        if not getattr(kernel, name)(c.byref(value)) or value.value <= 0:
            raise OSError('Host QPC query failed')
        return value.value

    ip = c.WinDLL('iphlpapi', use_last_error=True)
    ip.GetIfTable2Ex.argtypes, ip.GetIfTable2Ex.restype = [c.c_int, c.POINTER(c.c_void_p)], c.c_uint32
    ip.GetIfStackTable.argtypes, ip.GetIfStackTable.restype = [c.POINTER(c.c_void_p)], c.c_uint32
    ip.FreeMibTable.argtypes, ip.FreeMibTable.restype = [c.c_void_p], None
    frequency = clock('QueryPerformanceFrequency')
    utc_before = datetime.now(timezone.utc).isoformat()
    before = clock('QueryPerformanceCounter')
    pointer = c.c_void_p()
    rc = ip.GetIfTable2Ex(1, c.byref(pointer))
    if rc:
        raise OSError(rc, 'GetIfTable2Ex failed')
    rows = []
    try:
        if not pointer.value:
            raise ValueError('Null interface table')
        count = c.cast(pointer, c.POINTER(_Table)).contents.count
        _integer(count, MAX_ROWS, 1)
        for row in c.cast(pointer.value + _Table.rows.offset, c.POINTER(_Row * count)).contents:
            rows.append(dict(index=row.index, guid=str(uuid.UUID(bytes_le=bytes(row.guid))),
                luid=str(row.luid), flags=row.flags, type=row.type, physical=row.physical,
                oper_status=row.oper, admin_status=row.admin, media_connect_state=row.connect))
    finally:
        if pointer.value:
            ip.FreeMibTable(pointer)
    pointer = c.c_void_p()
    rc = ip.GetIfStackTable(c.byref(pointer))
    if rc:
        raise OSError(rc, 'GetIfStackTable failed')
    edges = []
    try:
        if not pointer.value:
            raise ValueError('Null interface stack table')
        count = c.cast(pointer, c.POINTER(_StackTable)).contents.count
        _integer(count, MAX_EDGES)
        for row in c.cast(pointer.value + _StackTable.rows.offset, c.POINTER(_StackRow * count)).contents:
            edges.append(dict(upper=row.upper, lower=row.lower))
    finally:
        if pointer.value:
            ip.FreeMibTable(pointer)
    after = clock('QueryPerformanceCounter')
    utc_after = datetime.now(timezone.utc).isoformat()
    selected = [row for row in rows if row['index'] == interface_index]
    if len(selected) != 1 or selected[0]['guid'] != expected_guid:
        raise ValueError('Snapshot target differs from requested identity')
    indexes = {row['index'] for row in rows}
    snapshot = dict(schema='ndis-topology/v1', clock='qpc', qpc_frequency_hz=str(frequency),
        qpc_before=str(before), qpc_after=str(after), utc_before=utc_before, utc_after=utc_after,
        observation_atomic=False, target={k: selected[0][k] for k in ('index', 'guid', 'luid')},
        rows=sorted(rows, key=lambda row: row['index']), edges=sorted(edges, key=lambda edge: (edge['upper'], edge['lower'])),
        unresolved_indices=sorted({i for edge in edges for i in edge.values() if i and i not in indexes}))
    validate_snapshot(snapshot)
    return snapshot


def decode_json(raw: bytes) -> Any:
    """Decode bounded JSON without duplicate keys or excessive nesting."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON field')
            result[key] = value
        return result
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('Evidence file exceeds size limit')
    def constant(value: str) -> None:
        raise ValueError('Nonfinite JSON constants are not permitted')
    try:
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=constant)
    except RecursionError:
        raise ValueError('Evidence JSON exceeds nesting limit') from None
    stack = [(iter([value]), 0)]
    while stack:
        iterator, depth = stack[-1]
        try:
            current = next(iterator)
        except StopIteration:
            stack.pop()
            continue
        if type(current) in (dict, list):
            if depth >= 64:
                raise ValueError('Evidence JSON exceeds nesting limit')
            stack.append((iter(current.values() if type(current) is dict else current), depth + 1))
    return value


def load_json(path: Path) -> Any:
    with path.open('rb') as stream:
        return decode_json(stream.read(MAX_FILE_BYTES + 1))


def write_json_new(path: Path, value: Any) -> None:
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    snapshot = commands.add_parser('snapshot', help='Read documented interface/stack tables; no OID request')
    snapshot.add_argument('--if-index', type=int, required=True)
    snapshot.add_argument('--expected-guid', required=True)
    snapshot.add_argument('--output', type=Path, required=True)
    analysis = commands.add_parser('correlate', help='Classify offline evidence; private details go to new output only')
    for name in ('before', 'after', 'query', 'events', 'health', 'output'):
        analysis.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError('Output already exists')
        if args.command == 'snapshot':
            result = capture_snapshot(args.if_index, str(uuid.UUID(args.expected_guid)))
            receipt = dict(snapshot_written=True, interface_count=len(result['rows']), stack_edge_count=len(result['edges']),
                           unresolved_vertex_count=len(result['unresolved_indices']), observation_atomic=False)
            exit_code = 0
        else:
            result = correlate(*(load_json(getattr(args, name)) for name in ('before', 'after', 'query', 'events', 'health')))
            receipt = {name: result[name] for name in ('classification', 'raw_statuses', 'reasons')}
            receipt['matching_event_count'] = len(result['matches'])
            exit_code = int(result['classification'] == 'rejected')
        write_json_new(args.output, result)
        print(json.dumps(receipt, sort_keys=True))
        return exit_code
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f'NDIS evidence rejected: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
