"""Thresholds, percentile slots and exact continuous-window membership."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import CONF_HIGH, CONF_LOW, PRICE_UNIT
from .descriptions import BINARY_SENSORS
from .entity import BkwEntity
from .price import in_window

async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities([BkwTariffBinarySensor(entry.runtime_data, d) for d in BINARY_SENSORS])

class BkwTariffBinarySensor(BkwEntity, BinarySensorEntity):
    def __init__(self, coordinator, description) -> None:
        super().__init__(coordinator, description.key)
        self.description = description
        self.key = description.key
        self._attr_entity_registry_enabled_default = description.enabled
        self._attr_icon = "mdi:calendar-clock" if description.kind == "membership" else "mdi:chart-line"
        if description.kind == "threshold":
            self._attr_icon = "mdi:trending-up" if self.key == "above_high" else "mdi:trending-down"

    @property
    def available(self) -> bool:
        return self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        snapshot = self.coordinator.snapshot
        if snapshot is None or snapshot["current"] is None:
            return None
        current = snapshot["current"]
        d = self.description
        if d.kind == "threshold":
            if self.key == "above_high":
                return current.price > self.coordinator.threshold(CONF_HIGH)
            return current.price < self.coordinator.threshold(CONF_LOW)
        if d.kind == "membership":
            return in_window(snapshot["today"]["windows"][f"{d.mode}_{d.hours}h"], snapshot["evaluated_at"])
        group = snapshot["today"]["rankings"][f"{d.mode}_{d.percent}"]
        if group is None:
            return None
        return any(s.start <= snapshot["evaluated_at"] < s.end for s in group["slots"])

    @property
    def extra_state_attributes(self):
        d, snapshot = self.description, self.coordinator.snapshot
        attrs = {"price_unit": PRICE_UNIT}
        if d.kind == "threshold":
            key = CONF_HIGH if self.key == "above_high" else CONF_LOW
            attrs.update(threshold=self.coordinator.threshold(key), comparison=">" if key == CONF_HIGH else "<")
        elif snapshot:
            attrs.update(evaluated_at=snapshot["evaluated_at"].isoformat(),
                         date=snapshot["today"]["stats"]["date"], timezone="Europe/Zurich",
                         complete=snapshot["today"]["stats"]["complete"])
            if d.kind == "membership":
                window = snapshot["today"]["windows"][f"{d.mode}_{d.hours}h"]
                attrs.update(start=window.start.isoformat() if window else None,
                             end=window.end.isoformat() if window else None,
                             average=window.average if window else None,
                             hours=d.hours, selection=d.mode, tie_break="earliest_start")
            else:
                group = snapshot["today"]["rankings"][f"{d.mode}_{d.percent}"]
                attrs.update(requested_percent=d.percent, selection=d.mode, include_price_ties=True)
                if group:
                    attrs.update({k: v for k, v in group.items() if k not in ("slots", "requested_percent")})
                    attrs["slots"] = [s.as_dict() for s in group["slots"]]
        return attrs
