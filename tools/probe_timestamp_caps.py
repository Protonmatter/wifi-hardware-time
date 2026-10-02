"""Read documented Windows timestamp capabilities for one explicit interface.

Usage: python probe_timestamp_caps.py --if-index 20
Requires Windows and Python only. No private OIDs, register access, packet sends,
configuration writes, or timestamp enabling. Cross timestamp is queried once only
when the active configuration advertises it. Exit 0 means queries completed;
unsupported capability is a recorded result, not an execution failure.
"""
import argparse
import ctypes as ct
import datetime
import json
import os
import sys

HW_FIELDS = (
    'PtpV2OverUdpIPv4EventMessageReceive', 'PtpV2OverUdpIPv4AllMessageReceive',
    'PtpV2OverUdpIPv4EventMessageTransmit', 'PtpV2OverUdpIPv4AllMessageTransmit',
    'PtpV2OverUdpIPv6EventMessageReceive', 'PtpV2OverUdpIPv6AllMessageReceive',
    'PtpV2OverUdpIPv6EventMessageTransmit', 'PtpV2OverUdpIPv6AllMessageTransmit',
    'AllReceive', 'AllTransmit', 'TaggedTransmit',
)
SW_FIELDS = ('AllReceive', 'AllTransmit', 'TaggedTransmit')


class Hardware(ct.Structure):
    _fields_ = [(name, ct.c_uint8) for name in HW_FIELDS]


class Software(ct.Structure):
    _fields_ = [(name, ct.c_uint8) for name in SW_FIELDS]


class Capabilities(ct.Structure):
    _fields_ = [('HardwareClockFrequencyHz', ct.c_uint64),
                ('SupportsCrossTimestamp', ct.c_uint8),
                ('HardwareCapabilities', Hardware),
                ('SoftwareCapabilities', Software)]


class CrossTimestamp(ct.Structure):
    _fields_ = [(name, ct.c_uint64) for name in
                ('SystemTimestamp1', 'HardwareClockTimestamp', 'SystemTimestamp2')]


def decode(value: Capabilities) -> dict[str, object]:
    return {
        'HardwareClockFrequencyHz': value.HardwareClockFrequencyHz,
        'SupportsCrossTimestamp': bool(value.SupportsCrossTimestamp),
        'HardwareCapabilities': {name: bool(getattr(value.HardwareCapabilities, name)) for name in HW_FIELDS},
        'SoftwareCapabilities': {name: bool(getattr(value.SoftwareCapabilities, name)) for name in SW_FIELDS},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--if-index', required=True, type=int)
    args = parser.parse_args()
    if os.name != 'nt' or not 0 < args.if_index <= 0xFFFFFFFF:
        parser.error('Requires Windows and a positive 32-bit interface index')
    # Layout checked against SDK 10.0.26100.0 iphlpapi.h.
    if (ct.sizeof(Capabilities), Capabilities.HardwareCapabilities.offset,
            Capabilities.SoftwareCapabilities.offset) != (24, 9, 20):
        raise RuntimeError('Unexpected native structure layout')
    ip = ct.WinDLL('iphlpapi.dll', use_last_error=True)
    convert = ip.ConvertInterfaceIndexToLuid
    convert.argtypes = [ct.c_uint32, ct.POINTER(ct.c_uint64)]
    convert.restype = ct.c_uint32
    luid = ct.c_uint64()
    rc = convert(args.if_index, ct.byref(luid))
    if rc:
        raise OSError(rc, ct.FormatError(rc))
    report = {'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'interface_index': args.if_index, 'interface_luid': hex(luid.value),
              'queries': {}}
    active = None
    for name in ('GetInterfaceSupportedTimestampCapabilities', 'GetInterfaceActiveTimestampCapabilities'):
        func = getattr(ip, name)
        func.argtypes = [ct.POINTER(ct.c_uint64), ct.POINTER(Capabilities)]
        func.restype = ct.c_uint32
        result = Capabilities()
        rc = func(ct.byref(luid), ct.byref(result))
        report['queries'][name] = {'return_code': rc, 'message': ct.FormatError(rc).strip(),
                                   'capabilities': decode(result) if rc == 0 else None}
        if name == 'GetInterfaceActiveTimestampCapabilities' and rc == 0:
            active = result
    if active is not None and active.SupportsCrossTimestamp:
        func = ip.CaptureInterfaceHardwareCrossTimestamp
        func.argtypes = [ct.POINTER(ct.c_uint64), ct.POINTER(CrossTimestamp)]
        func.restype = ct.c_uint32
        stamp = CrossTimestamp()
        rc = func(ct.byref(luid), ct.byref(stamp))
        report['cross_timestamp'] = {'return_code': rc, 'message': ct.FormatError(rc).strip(),
                                    'values': {name: getattr(stamp, name) for name, _ in stamp._fields_} if rc == 0 else None}
    else:
        reason = 'Active-capability query failed' if active is None else 'Active configuration does not advertise cross timestamps'
        report['cross_timestamp'] = {'queried': False, 'reason': reason}
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
