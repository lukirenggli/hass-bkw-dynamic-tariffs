"""Requested price sensors and API timestamp diagnostic."""
from datetime import datetime
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.util import dt as dt_util
from .const import PRICE_UNIT
from .entity import BkwEntity
from .price import current_slot, daily_statistics, minutes_to_change, next_change
KEYS = ("current_price","average_today","maximum_today","minimum_today","next_change","last_api_update")
ICONS = ("mdi:currency-chf","mdi:chart-bell-curve","mdi:arrow-up-bold","mdi:arrow-down-bold",
         "mdi:timer-outline","mdi:cloud-check-outline")

async def async_setup_entry(hass,entry,async_add_entities) -> None:
    async_add_entities([BkwSensor(entry.runtime_data,key) for key in KEYS])

class BkwSensor(BkwEntity,SensorEntity):
    _attr_suggested_display_precision = 4
    def __init__(self,coordinator,key:str) -> None:
        super().__init__(coordinator,key)
        self.key = key
        self._attr_icon = ICONS[KEYS.index(key)]
        if key == "last_api_update":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif key == "next_change":
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
            self._attr_suggested_display_precision = 0
        else:
            # Monetary expects CHF, not CHF/kWh. No incorrect device class.
            self._attr_native_unit_of_measurement = PRICE_UNIT
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None and self.native_value is not None

    @property
    def native_value(self) -> float | int | datetime | None:
        data = self.coordinator.data
        if data is None:
            return None
        now = dt_util.utcnow()
        if self.key == "last_api_update":
            return data.retrieved
        if self.key == "next_change":
            return minutes_to_change(data.slots,now)
        if self.key == "current_price":
            slot = current_slot(data.slots,now)
            return slot.price if slot else None
        stat = {"average_today":"average","maximum_today":"maximum","minimum_today":"minimum"}[self.key]
        value = daily_statistics(data.slots,now)[stat]
        return round(value,6) if value is not None else None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if data is None:
            return {}
        attrs = {"tariff_type":"feed_in","publication_timestamp":data.publication.isoformat(),
                 "last_api_success":self.coordinator.last_update_success}
        now = dt_util.utcnow()
        if self.key == "current_price":
            slot = current_slot(data.slots,now)
            attrs.update(interval_start=slot.start.isoformat() if slot else None,
                         interval_end=slot.end.isoformat() if slot else None,
                         prices=[s.as_dict() for s in data.slots])
        elif self.key == "next_change":
            change = next_change(data.slots,now)
            attrs["next_change_at"] = change.isoformat() if change else None
        elif self.key in ("average_today","minimum_today","maximum_today"):
            attrs.update({k:v for k,v in daily_statistics(data.slots,now).items()
                          if k not in ("average","minimum","maximum")})
        return attrs
