"""Twelve-hour network polling, separate minute/interval clock for cached prices."""
from datetime import datetime, timedelta
import logging
from math import isfinite
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from .api import BkwApi, BkwApiError
from .const import (CONF_HIGH, CONF_LOW, DEFAULT_HIGH, DEFAULT_LOW, MAX_THRESHOLD,
                    MIN_THRESHOLD, NAME, UPDATE_INTERVAL)
from .price import InvalidTariffs, TariffData, merge_tariffs
_LOGGER = logging.getLogger(__name__)

class BkwCoordinator(DataUpdateCoordinator[TariffData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: BkwApi) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=NAME, update_interval=UPDATE_INTERVAL)
        self.entry = entry
        self.api = api
        self._cancel_tick: CALLBACK_TYPE | None = None

    async def _async_update_data(self) -> TariffData:
        try:
            incoming = await self.api.async_fetch()
            result = merge_tariffs(self.data, incoming, dt_util.utcnow())
            if not result.slots:
                raise InvalidTariffs("No current or future tariffs published")
            return result
        except (BkwApiError, InvalidTariffs) as err:
            raise UpdateFailed(str(err)) from err

    def threshold(self, key: str) -> float:
        default = DEFAULT_HIGH if key == CONF_HIGH else DEFAULT_LOW
        return float(self.entry.options.get(key, self.entry.data.get(key, default)))

    @callback
    def set_threshold(self, key: str, value: float) -> None:
        low = value if key == CONF_LOW else self.threshold(CONF_LOW)
        high = value if key == CONF_HIGH else self.threshold(CONF_HIGH)
        if not isfinite(value) or not MIN_THRESHOLD <= value <= MAX_THRESHOLD or low > high:
            raise ValueError("Lower threshold must not exceed upper threshold; range -10 to 10 CHF/kWh")
        options = dict(self.entry.options)
        options[key] = value
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        self.async_update_listeners()

    @callback
    def start_clock(self) -> None:
        self._schedule_tick()

    @callback
    def stop_clock(self) -> None:
        if self._cancel_tick:
            self._cancel_tick()
            self._cancel_tick = None

    @callback
    def _schedule_tick(self) -> None:
        self.stop_clock()
        now = dt_util.utcnow()
        when = now.replace(second=0,microsecond=0) + timedelta(minutes=1)
        if self.data:
            for slot in self.data.slots:
                for boundary in (slot.start,slot.end):
                    if now < boundary < when:
                        when = boundary
        self._cancel_tick = async_track_point_in_utc_time(self.hass,self._tick,when)

    @callback
    def _tick(self, now: datetime) -> None:
        self._cancel_tick = None
        # Do NOT use async_set_updated_data: it resets the API polling timer.
        self.async_update_listeners()
        self._schedule_tick()

    @callback
    def _async_refresh_finished(self) -> None:
        if self._cancel_tick is not None:
            self._schedule_tick()
