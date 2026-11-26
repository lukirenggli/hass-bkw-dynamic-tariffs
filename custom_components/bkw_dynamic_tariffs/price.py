"""Strict VSE parsing and pure timezone-aware tariff calculations."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from math import ceil, isfinite
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo
UTC = timezone.utc
ZURICH = ZoneInfo("Europe/Zurich")

class InvalidTariffs(ValueError):
    """Invalid, unsupported or ambiguous API data."""

@dataclass(frozen=True)
class PriceSlot:
    """UTC interval, including start and excluding end."""
    start: datetime
    end: datetime
    price: float
    def as_dict(self) -> dict[str, Any]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "price": self.price}

@dataclass(frozen=True)
class TariffData:
    """Immutable, validated response."""
    slots: tuple[PriceSlot, ...]
    publication: datetime
    retrieved: datetime

def parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise InvalidTariffs("Missing timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as err:
        raise InvalidTariffs("Invalid timestamp") from err
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InvalidTariffs("Timestamp must include timezone")
    return parsed.astimezone(UTC)

def parse_tariffs(payload: Any, retrieved: datetime) -> TariffData:
    """Reject malformed rows; do not silently substitute zero or drop bad prices."""
    if not isinstance(payload, dict):
        raise InvalidTariffs("Expected an object")
    publication = parse_timestamp(payload.get("publication_timestamp"))
    rows = payload.get("prices")
    if not isinstance(rows, list) or not rows:
        raise InvalidTariffs("No tariff prices published")
    slots = []
    for row in rows:
        if not isinstance(row, dict):
            raise InvalidTariffs("Invalid interval")
        start = parse_timestamp(row.get("start_timestamp"))
        end = parse_timestamp(row.get("end_timestamp"))
        if start >= end:
            raise InvalidTariffs("Interval must have positive duration")
        components = row.get("feed_in")
        if not isinstance(components, list) or not components:
            raise InvalidTariffs("Missing feed_in price")
        values = []
        for component in components:
            if not isinstance(component, dict) or component.get("unit") != "CHF_kWh":
                raise InvalidTariffs("Unsupported feed_in unit; expected CHF_kWh")
            value = component.get("value")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise InvalidTariffs("Invalid numeric price")
            value = float(value)
            if not isfinite(value):
                raise InvalidTariffs("Non-finite price")
            values.append(value)
        price = sum(values)
        if not isfinite(price):
            raise InvalidTariffs("Non-finite total price")
        slots.append(PriceSlot(start, end, price))
    slots.sort(key=lambda slot: slot.start)
    for previous, following in zip(slots, slots[1:]):
        if following.start < previous.end:
            raise InvalidTariffs("Duplicate or overlapping intervals")
    return TariffData(tuple(slots), publication, retrieved)

def day_bounds(now: datetime, offset: int = 0) -> tuple[datetime, datetime]:
    """Actual Swiss-day UTC bounds, respecting 23/24/25-hour DST days."""
    day = now.astimezone(ZURICH).date() + timedelta(days=offset)
    return (datetime.combine(day, time.min, ZURICH).astimezone(UTC),
            datetime.combine(day + timedelta(days=1), time.min, ZURICH).astimezone(UTC))

def current_slot(slots: tuple[PriceSlot, ...], now: datetime) -> PriceSlot | None:
    return next((slot for slot in slots if slot.start <= now < slot.end), None)

def next_change(slots: tuple[PriceSlot, ...], now: datetime) -> datetime | None:
    """Next different contiguous price, not just the next quarter-hour."""
    active = current_slot(slots, now)
    if active is None:
        return None
    edge = active.end
    for following in slots:
        if following.start < edge:
            continue
        if following.start != edge:
            return None
        if following.price != active.price:
            return following.start
        edge = following.end
    return None

def minutes_to_change(slots: tuple[PriceSlot, ...], now: datetime) -> int | None:
    change = next_change(slots, now)
    return ceil((change - now).total_seconds() / 60) if change else None

def daily_statistics(slots: tuple[PriceSlot, ...], now: datetime) -> dict[str, Any]:
    """Only a complete Swiss day yields mean/min/max; never fabricate gaps."""
    start, end = day_bounds(now)
    parts = [(max(slot.start, start), min(slot.end, end), slot.price)
             for slot in slots if slot.start < end and slot.end > start]
    covered = sum((b-a).total_seconds() for a,b,_ in parts)
    total = (end-start).total_seconds()
    complete = bool(parts) and parts[0][0] == start and parts[-1][1] == end
    complete = complete and all(a[1] == b[0] for a,b in zip(parts,parts[1:]))
    result = {"date": now.astimezone(ZURICH).date().isoformat(), "timezone": "Europe/Zurich",
              "complete": complete, "coverage_percent": round(100*covered/total,2),
              "covered_minutes": round(covered/60,2), "expected_minutes": int(total/60),
              "slots_count": len(parts), "average": None, "minimum": None, "maximum": None}
    if complete:
        result.update(average=sum((b-a).total_seconds()*p for a,b,p in parts)/total,
                      minimum=min(p for _,_,p in parts), maximum=max(p for _,_,p in parts))
    return result

def merge_tariffs(previous: TariffData | None, incoming: TariffData, now: datetime) -> TariffData:
    """Replace incoming range including gaps, retain cached other days."""
    if previous is not None and incoming.publication < previous.publication:
        raise InvalidTariffs("API publication timestamp moved backwards")
    keep_from,_ = day_bounds(now)
    start,end = incoming.slots[0].start,incoming.slots[-1].end
    retained = [] if previous is None else [s for s in previous.slots
                if s.end > keep_from and (s.end <= start or s.start >= end)]
    merged = sorted([*retained,*incoming.slots], key=lambda s:s.start)
    return TariffData(tuple(s for s in merged if s.end > keep_from), incoming.publication, incoming.retrieved)


@dataclass(frozen=True)
class PriceWindow:
    """An actual elapsed-time continuous window, restricted to one Swiss day."""
    start: datetime
    end: datetime
    average: float
    hours: int
    mode: str

    def as_dict(self) -> dict[str, Any]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(),
                "average": self.average, "hours": self.hours, "mode": self.mode,
                "timezone": "Europe/Zurich"}


def slots_for_day(slots: tuple[PriceSlot, ...], now: datetime, offset: int = 0) -> tuple[PriceSlot, ...]:
    """Clip intervals to the specified local day, excluding other days."""
    start, end = day_bounds(now, offset)
    return tuple(PriceSlot(max(start, s.start), min(end, s.end), s.price)
                 for s in slots if s.start < end and s.end > start)


def extreme_window(slots: tuple[PriceSlot, ...], now: datetime, hours: int,
                   mode: str, offset: int = 0) -> PriceWindow | None:
    """Optimize over all relevant starts and ends, with duration weighting.

Only complete days are ranked. With piecewise-constant prices an optimum occurs
when either window edge is a tariff boundary. This also handles nonuniform slots.
Equal averages (within 12-decimal precision) select the earliest UTC start.
"""
    if hours <= 0 or mode not in ("cheap", "expensive"):
        raise ValueError("Invalid window definition")
    selected = slots_for_day(slots, now, offset)
    start, end = day_bounds(now, offset)
    if not daily_statistics(selected, start)["complete"]:
        return None
    duration = timedelta(hours=hours)
    if end-start < duration:
        return None
    boundaries = {start, end}
    for slot in selected:
        boundaries.update((slot.start, slot.end))
    candidates = {b for b in boundaries if start <= b <= end-duration}
    candidates.update(b-duration for b in boundaries if start <= b-duration <= end-duration)
    windows = []
    for begin in sorted(candidates):
        finish = begin+duration
        weighted = sum((min(finish, s.end)-max(begin, s.start)).total_seconds()*s.price
                       for s in selected if s.start < finish and s.end > begin)
        windows.append(PriceWindow(begin, finish, weighted/duration.total_seconds(), hours, mode))
    # min uses start as deterministic tie-breaker; never compare datetime wall-clock
    # durations in Zurich because repeated autumn hours have different UTC offsets.
    return min(windows, key=lambda w: (round(w.average, 12) if mode == "cheap"
                                      else -round(w.average, 12), w.start))


def ranked_slots(slots: tuple[PriceSlot, ...], now: datetime, fraction: float,
                 mode: str) -> dict[str, Any] | None:
    """Rank today's slots; include all price ties at the percentile threshold."""
    if not 0 < fraction <= 1 or mode not in ("cheap", "expensive"):
        raise ValueError("Invalid ranking")
    selected = slots_for_day(slots, now)
    if not daily_statistics(selected, now)["complete"]:
        return None
    prices = sorted((s.price for s in selected), reverse=mode == "expensive")
    threshold = prices[ceil(len(prices)*fraction)-1]
    qualifying = tuple(s for s in selected if (s.price <= threshold if mode == "cheap"
                                               else s.price >= threshold))
    return {"threshold": threshold, "slots": qualifying,
            "requested_percent": fraction*100, "selected_slots": len(qualifying),
            "total_slots": len(selected), "actual_percent": 100*len(qualifying)/len(selected)}


def in_window(window: PriceWindow | None, now: datetime) -> bool | None:
    """Half-open interval membership; unknown is not false."""
    return window.start <= now < window.end if window else None


@lru_cache(maxsize=8)
def _day_metrics(slots: tuple[PriceSlot, ...], date_text: str) -> dict[str, Any]:
    """Cache date-dependent expensive rankings, not time-dependent entity states."""
    local_midnight = datetime.fromisoformat(date_text).replace(tzinfo=ZURICH).astimezone(UTC)
    metrics = {"stats": daily_statistics(slots, local_midnight), "windows": {}, "rankings": {}}
    for mode in ("cheap", "expensive"):
        for hours in (2, 4):
            metrics["windows"][f"{mode}_{hours}h"] = extreme_window(slots, local_midnight, hours, mode)
        for percent in (10, 25, 50):
            metrics["rankings"][f"{mode}_{percent}"] = ranked_slots(slots, local_midnight, percent/100, mode)
    return metrics


def build_snapshot(slots: tuple[PriceSlot, ...], now: datetime) -> dict[str, Any]:
    """One coherent evaluation time for every entity during a local/API update."""
    today = now.astimezone(ZURICH).date()
    tomorrow = today+timedelta(days=1)
    future = tuple(s for s in slots if s.start > now)
    return {"evaluated_at": now, "current": current_slot(slots, now),
            "next_change": next_change(slots, now), "minutes_to_change": minutes_to_change(slots, now),
            "today": _day_metrics(slots, today.isoformat()),
            "tomorrow": _day_metrics(slots, tomorrow.isoformat()),
            "forecast": future, "next_tariff": future[0] if future else None}
