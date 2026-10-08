"""Read the connected BSS's cached beacon timestamp through the public WLAN API.

Read-only. WlanGetNetworkBssList returns the WLAN service cache; no scan is
requested and no setting changes. Cache age is unknown, so the value supports
only the coarse shared-clock check. BSSIDs are hashed before leaving this module.
"""
from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass
import hashlib
import struct
from typing import Callable
import uuid

ENTRY_SIZE = 360
HEADER_SIZE = 8
CURRENT_CONNECTION = 7  # wlan_intf_opcode_current_connection
INFRASTRUCTURE = 1  # dot11_BSS_type_infrastructure


class GUID(ct.Structure):
    _fields_ = [('Data1', ct.c_uint32), ('Data2', ct.c_uint16), ('Data3', ct.c_uint16), ('Data4', ct.c_ubyte * 8)]


class DOT11_SSID(ct.Structure):
    _fields_ = [('uSSIDLength', ct.c_uint32), ('ucSSID', ct.c_ubyte * 32)]


class WLAN_RATE_SET(ct.Structure):
    _fields_ = [('uRateSetLength', ct.c_uint32), ('usRateSet', ct.c_uint16 * 126)]


class WLAN_BSS_ENTRY(ct.Structure):
    _fields_ = [('dot11Ssid', DOT11_SSID), ('uPhyId', ct.c_uint32), ('dot11Bssid', ct.c_ubyte * 6),
                ('dot11BssType', ct.c_int), ('dot11BssPhyType', ct.c_int), ('lRssi', ct.c_int32),
                ('uLinkQuality', ct.c_uint32), ('bInRegDomain', ct.c_ubyte), ('usBeaconPeriod', ct.c_uint16),
                ('ullTimestamp', ct.c_uint64), ('ullHostTimestamp', ct.c_uint64),
                ('usCapabilityInformation', ct.c_uint16), ('ulChCenterFrequency', ct.c_uint32),
                ('wlanRateSet', WLAN_RATE_SET), ('ulIeOffset', ct.c_uint32), ('ulIeSize', ct.c_uint32)]


class WLAN_ASSOCIATION_ATTRIBUTES(ct.Structure):
    _fields_ = [('dot11Ssid', DOT11_SSID), ('dot11BssType', ct.c_int), ('dot11Bssid', ct.c_ubyte * 6),
                ('dot11PhyType', ct.c_int), ('uDot11PhyIndex', ct.c_uint32), ('wlanSignalQuality', ct.c_uint32),
                ('ulRxRate', ct.c_uint32), ('ulTxRate', ct.c_uint32)]


class WLAN_SECURITY_ATTRIBUTES(ct.Structure):
    _fields_ = [('bSecurityEnabled', ct.c_int), ('bOneXEnabled', ct.c_int),
                ('dot11AuthAlgorithm', ct.c_int), ('dot11CipherAlgorithm', ct.c_int)]


class WLAN_CONNECTION_ATTRIBUTES(ct.Structure):
    _fields_ = [('isState', ct.c_int), ('wlanConnectionMode', ct.c_int), ('strProfileName', ct.c_wchar * 256),
                ('wlanAssociationAttributes', WLAN_ASSOCIATION_ATTRIBUTES),
                ('wlanSecurityAttributes', WLAN_SECURITY_ATTRIBUTES)]


def parse_bss_list(buffer: bytes, bssid: bytes) -> list[int]:
    """Return ullTimestamp for every entry whose BSSID matches."""
    if len(buffer) < HEADER_SIZE:
        raise ValueError('Short BSS list')
    total, count = struct.unpack_from('<II', buffer)
    if total > len(buffer) or HEADER_SIZE + count * ENTRY_SIZE > len(buffer):
        raise ValueError('BSS list exceeds its buffer')
    stamps = []
    for index in range(count):
        item = WLAN_BSS_ENTRY.from_buffer_copy(buffer, HEADER_SIZE + index * ENTRY_SIZE)
        if bytes(item.dot11Bssid) == bssid:
            stamps.append(item.ullTimestamp)
    return stamps


class CacheEntryUnavailable(Exception):
    """The cache held zero or several entries for the connected BSSID; skip this read."""

    def __init__(self, count: int):
        super().__init__(f'Connected BSS present {count} times in the cache')
        self.count = count


def single_stamp(stamps: list[int]) -> int:
    if len(stamps) != 1:
        raise CacheEntryUnavailable(len(stamps))
    return stamps[0]


@dataclass(frozen=True)
class BeaconRead:
    qpc_before: int
    qpc_after: int
    ap_tsf_us: int
    bssid_sha256: str


class BssReader:
    def __init__(self, interface_guid: str):
        self.api = ct.WinDLL('wlanapi.dll')
        self.api.WlanOpenHandle.argtypes = [ct.c_uint32, ct.c_void_p, ct.POINTER(ct.c_uint32), ct.POINTER(ct.c_void_p)]
        self.api.WlanCloseHandle.argtypes = [ct.c_void_p, ct.c_void_p]
        self.api.WlanFreeMemory.argtypes = [ct.c_void_p]
        self.api.WlanQueryInterface.argtypes = [ct.c_void_p, ct.POINTER(GUID), ct.c_int, ct.c_void_p,
                                                ct.POINTER(ct.c_uint32), ct.POINTER(ct.c_void_p), ct.c_void_p]
        self.api.WlanGetNetworkBssList.argtypes = [ct.c_void_p, ct.POINTER(GUID), ct.c_void_p, ct.c_int,
                                                   ct.c_int, ct.c_void_p, ct.POINTER(ct.c_void_p)]
        self.guid = GUID.from_buffer_copy(uuid.UUID(interface_guid).bytes_le)
        version, handle = ct.c_uint32(), ct.c_void_p()
        status = self.api.WlanOpenHandle(2, None, ct.byref(version), ct.byref(handle))
        if status:
            raise OSError(status, 'WlanOpenHandle failed')
        self.handle = handle

    def close(self) -> None:
        if self.handle:
            self.api.WlanCloseHandle(self.handle, None)
            self.handle = None

    def connected_bssid(self) -> bytes:
        size, data = ct.c_uint32(), ct.c_void_p()
        status = self.api.WlanQueryInterface(self.handle, ct.byref(self.guid), CURRENT_CONNECTION, None,
                                             ct.byref(size), ct.byref(data), None)
        if status:
            raise OSError(status, 'WlanQueryInterface failed')
        try:
            if size.value < ct.sizeof(WLAN_CONNECTION_ATTRIBUTES):
                raise ValueError('Short connection attributes')
            attributes = WLAN_CONNECTION_ATTRIBUTES.from_address(data.value)
            return bytes(attributes.wlanAssociationAttributes.dot11Bssid)
        finally:
            self.api.WlanFreeMemory(data)

    def read(self, qpc: Callable[[], int]) -> BeaconRead:
        bssid = self.connected_bssid()
        listing = ct.c_void_p()
        before = qpc()
        status = self.api.WlanGetNetworkBssList(self.handle, ct.byref(self.guid), None, INFRASTRUCTURE, 0, None,
                                                ct.byref(listing))
        after = qpc()
        if status:
            raise OSError(status, 'WlanGetNetworkBssList failed')
        try:
            total = ct.c_uint32.from_address(listing.value).value
            stamps = parse_bss_list(ct.string_at(listing.value, total), bssid)
        finally:
            self.api.WlanFreeMemory(listing)
        if self.connected_bssid() != bssid:
            raise RuntimeError('Association changed during the read')
        return BeaconRead(before, after, single_stamp(stamps), hashlib.sha256(bssid).hexdigest())
