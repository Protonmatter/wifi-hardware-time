"""Pure conservative lifecycle model. An accepted report is not a clock mapping.

Restarting acquisition assumes an externally isolated/drained session; this
model cannot identify late firmware reports without a transaction identifier.
"""
from dataclasses import dataclass


@dataclass
class Lifecycle:
    max_age_ticks: int
    epoch: int = 0
    state: str = 'unavailable'
    reason: str = 'not_started'
    last_tick: int = -1
    last_report: int | None = None
    last_counter: int | None = None
    pending: int | None = None
    last_sequence: int = 0

    def __post_init__(self) -> None:
        if type(self.max_age_ticks) is not int or self.max_age_ticks <= 0:
            raise ValueError('Require a positive freshness policy, not an accuracy bound')

    def _time(self, tick: int) -> None:
        if type(tick) is not int or tick < 0 or tick < self.last_tick:
            self.state='invalid';self.reason='host_clock_regression'
            raise ValueError(self.reason)
        self.last_tick=tick

    def start(self, source: str, build: str, tick: int) -> None:
        self._time(tick)
        if not source or not build: raise ValueError('Missing source identity')
        self.epoch+=1;self.state='acquiring';self.reason='new_acquisition_epoch'
        self.pending=None;self.last_report=None;self.last_counter=None;self.last_sequence=0

    def invalidate(self, reason: str, tick: int) -> None:
        self._time(tick)
        self.state='invalid';self.reason=reason;self.pending=None

    def request(self, sequence: int, tick: int) -> None:
        self._time(tick)
        if self.state not in ('acquiring','observed') or self.pending is not None or type(sequence) is not int or sequence <= self.last_sequence:
            self.invalidate('ambiguous_request',tick)
            raise ValueError(self.reason)
        self.pending=sequence;self.last_sequence=sequence

    def report(self, sequence: int, tick: int, counter: int) -> None:
        self._time(tick)
        if (self.state not in ('acquiring','observed') or self.pending != sequence or
            type(sequence) is not int or type(counter) is not int or not 0 <= counter < (1 << 64) or
            (self.last_counter is not None and counter <= self.last_counter)):
            self.invalidate('ambiguous_or_discontinuous_report',tick)
            raise ValueError(self.reason)
        self.pending=None;self.last_report=tick;self.last_counter=counter
        self.state='observed';self.reason='experimental_observation_only'

    def usable(self, tick: int) -> bool:
        self._time(tick)
        if self.state == 'observed' and self.last_report is not None and tick-self.last_report > self.max_age_ticks:
            self.invalidate('expired',tick)
        return self.state == 'observed'
