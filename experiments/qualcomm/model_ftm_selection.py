"""Offline model of post-filter FTM selection in the pinned Qualcomm driver.

Input is the two eight-slot arrays printed by PrintRttResults after filtering.
This models RVAs 0x14653c..0x146724, not firmware sampling or the whole driver.
No device I/O, calibration, or replacement ranging algorithm is provided.
"""
from dataclasses import dataclass
from typing import Sequence

EMPTY = -(1 << 31)


@dataclass(frozen=True)
class Selection:
    channel_counts: tuple[int, int]
    channel_means: tuple[int, int]
    selected_channel: int | None
    selected_count: int
    selected_rtt_raw: int
    auxiliary_raw: int


def _values(slots: Sequence[int]) -> list[int]:
    if len(slots) != 8:
        raise ValueError("Expected eight post-filter slots per channel")
    if any(type(value) is not int or not EMPTY <= value < (1 << 31) for value in slots):
        raise ValueError("Slots must be signed 32-bit integers")
    return [value for value in slots if value != EMPTY]


def _mean(values: list[int]) -> int:
    # AArch64 SDIV truncates toward zero; Python // rounds toward minus infinity.
    total = sum(values)
    return (-1 if total < 0 else 1) * (abs(total) // len(values))


def select_postfilter(ch0: Sequence[int], ch1: Sequence[int]) -> Selection:
    """Reproduce selection, including the empty-channel -1 comparison.

    The auxiliary field follows the observed UDIV on a 64-bit numerator, even
    for negative sums. It is deliberately not called a variance or uncertainty.
    All-empty input takes a different branch: zero RTT, with its presence bit
    cleared in the driver's WDI object. This model does not emulate OS marshalling.
    """
    values = (_values(ch0), _values(ch1))
    counts = (len(values[0]), len(values[1]))
    means = tuple(_mean(channel) if channel else -1 for channel in values)
    if not sum(counts):
        return Selection(counts, means, None, 0, 0, 0)
    selected = 0 if means[0] <= means[1] else 1
    numerator = sum(count * mean for count, mean in zip(counts, means))
    auxiliary = (numerator & ((1 << 64) - 1)) // sum(counts)
    if counts[selected] == 0:
        auxiliary = 0
    return Selection(counts, means, selected, counts[selected], means[selected], auxiliary)
