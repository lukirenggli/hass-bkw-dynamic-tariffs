"""Entity inventory: exact screenshot defaults, plus an enabled tariff forecast."""
from dataclasses import dataclass

@dataclass(frozen=True)
class TariffDescription:
    key: str
    enabled: bool = True
    kind: str = "price"
    day: str = "today"
    mode: str = "cheap"
    hours: int = 0
    percent: int = 0

SENSORS = (
    TariffDescription("current_price"),
    TariffDescription("average_today", kind="average"),
    TariffDescription("maximum_today", kind="maximum"),
    TariffDescription("minimum_today", kind="minimum"),
    TariffDescription("next_change", kind="countdown"),
    TariffDescription("last_api_update", kind="diagnostic"),
    TariffDescription("forecast", kind="forecast"),
    TariffDescription("average_tomorrow", False, "average", "tomorrow"),
    *(TariffDescription(f"{mode}_{hours}h_{day}",
                       enabled=(mode == "cheap" and hours == 4 and day == "tomorrow"),
                       kind="window", day=day, mode=mode, hours=hours)
      for mode in ("cheap", "expensive") for hours in (2, 4) for day in ("today", "tomorrow")),
)
BINARY_SENSORS = (
    TariffDescription("above_high", kind="threshold"),
    TariffDescription("below_low", kind="threshold"),
    *(TariffDescription(f"{mode}_{percent}_today", False, "rank", percent=percent, mode=mode)
      for mode in ("cheap", "expensive") for percent in (10, 25, 50)),
    *(TariffDescription(f"in_{mode}_{hours}h_today",
                       enabled=(mode == "cheap" and hours == 4), kind="membership", mode=mode, hours=hours)
      for mode in ("cheap", "expensive") for hours in (2, 4)),
)
