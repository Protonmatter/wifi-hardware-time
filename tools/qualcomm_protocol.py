"""Pure validation for the one qualified Qualcomm binary and three commands."""
import hashlib
import struct

import pefile

QUALIFIED_SHA256 = 'ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115'
COMMANDS = {
    'get_hostdbglvl': (63, (0, 87, 0, 0)),
    'get_hostdbgout': (67, (0, 146, 0, 0)),
    'tsf_read_value': (306, (1, 230, 1, 0)),
}


def validate_driver(data: bytes) -> None:
    if hashlib.sha256(data).hexdigest() != QUALIFIED_SHA256:
        raise ValueError('Driver hash is not the qualified build; requalification is required')
    pe = pefile.PE(data=data)
    if pe.FILE_HEADER.Machine != 0xAA64:
        raise ValueError('Expected the qualified ARM64 architecture')
    if pe.get_data(0x18EA00, 12) != bytes.fromhex('9f020071680080520285881a'):
        raise ValueError('Unexpected TSF action-selection instructions')
    for name, (index, fields) in COMMANDS.items():
        record = pe.get_data(0x33BDE0 + index * 28, 28)
        if (len(record) != 28 or struct.unpack_from('<IIBB', record) != fields
                or record[10:].split(b'\0')[0] != name.encode('ascii')):
            raise ValueError(f'Unexpected command-table record: {name}')
    for selector, target in ((0xE5, 0x1263B4), (0xE6, 0x1263C8)):
        delta = struct.unpack('<i', pe.get_data(0x12677C + selector * 4, 4))[0]
        if 0x1257FC + delta * 4 != target:
            raise ValueError('Unexpected TSF dispatcher jump table')


def build_request(command: str, mac: bytes, *, tsf_action: int = 3) -> bytes:
    if command not in COMMANDS:
        raise ValueError('Unqualified command')
    if type(tsf_action) is not int or tsf_action not in (3, 4):
        raise ValueError('Only TSF READ_VALUE (3) and QTIMER_CAPTURE (4) are allowed')
    if command != 'tsf_read_value' and tsf_action != 3:
        raise ValueError('QTIMER_CAPTURE requires tsf_read_value')
    if len(mac) != 6 or not any(mac) or mac[0] & 1:
        raise ValueError('Require one nonzero unicast MAC selector')
    name = command.encode('ascii')
    if len(name) >= 20:
        raise ValueError('Command name exceeds fixed field')
    payload = bytearray(128)
    payload[:len(name)] = name
    payload[20:26] = mac
    if command == 'tsf_read_value':
        payload[28] = 1
        struct.pack_into('<I', payload, 32, 1 if tsf_action == 3 else 0)
    return bytes(payload)
