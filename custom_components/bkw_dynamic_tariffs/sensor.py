"""Current prices, day statistics, continuous windows and published future tariffs."""
from datetime import datetime
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime
from .const import PRICE_UNIT
from .descriptions import SENSORS
from .entity import BkwEntity

async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities([BkwSensor(entry.runtime_data, description) for description in SENSORS])

class BkwSensor(BkwEntity, SensorEntity):
    """Read one coordinator snapshot; no independent clock or HTTP requests."""
    _attr_suggested_display_precision = 4

    def __init__(self, coordinator, description) -> None:
        super().__init__(coordinator, description.key)
        self.description = description
        self.key = description.key
        self._attr_entity_registry_enabled_default = description.enabled
        self._attr_icon = "mdi:currency-chf"
        if description.kind == "diagnostic":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:cloud-check-outline"
        elif description.kind == "countdown":
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
            self._attr_suggested_display_precision = 0
            self._attr_icon = "mdi:timer-outline"
        else:
            self._attr_native_unit_of_measurement = PRICE_UNIT
            if description.kind != "forecast":
                self._attr_state_class = SensorStateClass.MEASUREMENT
            if description.kind == "window":
                self._attr_icon = "mdi:calendar-clock"
            elif description.kind == "forecast":
                self._attr_icon = "mdi:chart-timeline-variant"
            elif description.kind == "average":
                self._attr_icon = "mdi:chart-bell-curve"
            elif description.kind == "maximum":
                self._attr_icon = "mdi:arrow-up-bold"
            elif description.kind == "minimum":
                self._attr_icon = "mdi:arrow-down-bold"

    @property
    def available(self) -> bool:
        return self.native_value is not None

    @property
    def native_value(self) -> float | int | datetime | None:
        data, snapshot = self.coordinator.data, self.coordinator.snapshot
        if data is None or snapshot is None:
            return None
        kind = self.description.kind
        if kind == "diagnostic":
            return data.retrieved
        if kind == "countdown":
            return snapshot["minutes_to_change"]
        if kind == "price":
            return snapshot["current"].price if snapshot["current"] else None
        if kind == "forecast":
            return snapshot["next_tariff"].price if snapshot["next_tariff"] else None
        metrics = snapshot[self.description.day]
        if kind == "window":
            window = metrics["windows"][f"{self.description.mode}_{self.description.hours}h"]
            return round(window.average, 6) if window else None
        value = metrics["stats"][kind]
        return round(value, 6) if value is not None else None

    @property
    def extra_state_attributes(self):
        data, snapshot = self.coordinator.data, self.coordinator.snapshot
        if data is None or snapshot is None:
            return {}
        attrs = {"tariff_type": "feed_in", "publication_timestamp": data.publication.isoformat(),
                 "last_api_success": self.coordinator.last_update_success,
                 "evaluated_at": snapshot["evaluated_at"].isoformat()}
        kind = self.description.kind
        if kind == "price":
            slot = snapshot["current"]
            attrs.update(interval_start=slot.start.isoformat() if slot else None,
                         interval_end=slot.end.isoformat() if slot else None,
                         prices=[s.as_dict() for s in data.slots])
        elif kind == "countdown":
            change = snapshot["next_change"]
            attrs["next_change_at"] = change.isoformat() if change else None
        elif kind == "diagnostic":
            attrs.update(local_updated_at=self.coordinator.local_updated_at.isoformat(),
                         last_api_attempt=self.coordinator.last_api_attempt.isoformat()
                         if self.coordinator.last_api_attempt else None,
                         api_poll_interval_hours=12)
        elif kind == "forecast":
            future = snapshot["forecast"]
            attrs.update(forecast=[s.as_dict() for s in future],
                         forecast_count=len(future), price_unit=PRICE_UNIT,
                         forecast_start=future[0].start.isoformat() if future else None,
                         forecast_end=future[-1].end.isoformat() if future else None,
                         contiguous=all(a.end == b.start for a, b in zip(future, future[1:])),
                         source="BKW published tariffs", prediction_model=False)
        else:
            metrics = snapshot[self.description.day]
            attrs.update({k: v for k, v in metrics["stats"].items()
                          if k not in ("average", "minimum", "maximum")})
            if kind == "window":
                window = metrics["windows"][f"{self.description.mode}_{self.description.hours}h"]
                attrs.update(start=window.start.isoformat() if window else None,
                             end=window.end.isoformat() if window else None,
                             hours=self.description.hours, selection=self.description.mode,
                             tie_break="earliest_start", price_unit=PRICE_UNIT)
        return attrs
