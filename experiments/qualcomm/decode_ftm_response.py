"""Decode the pinned internal Windows FTM callback record; omit BSSID/location.

104-byte stride verified in wlanapi.dll; fields verified in its installed
locationframework.dll consumer. The wrapper pins both files. No network I/O.
"""
import argparse
import json
import struct
from pathlib import Path


def decode(data: bytes) -> dict[str, int | bool]:
    if len(data)!=104:raise ValueError('Expected one 104-byte FTM result')
    status=struct.unpack_from('<I',data,8)[0]
    result={'reported_target_status':status,'distance_accuracy_validated':False}
    if status:return result
    measurements=struct.unpack_from('<H',data,14)[0]
    if measurements==0:raise ValueError('Successful target has zero measurements')
    result.update(reported_measurement_count=measurements,
                  reported_rssi_dbm=struct.unpack_from('<i',data,16)[0],
                  reported_link_quality=struct.unpack_from('<I',data,20)[0],
                  reported_bandwidth_enum=struct.unpack_from('<I',data,24)[0],
                  reported_rtt_ps=struct.unpack_from('<i',data,28)[0],
                  reported_rtt_variance_raw=struct.unpack_from('<Q',data,32)[0])
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('response',type=Path)
    parser.add_argument('--output',type=Path,help='Optional local JSON output; default is <response-stem>.json')
    args=parser.parse_args()
    result=decode(args.response.read_bytes())
    (args.output or args.response.with_suffix('.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
