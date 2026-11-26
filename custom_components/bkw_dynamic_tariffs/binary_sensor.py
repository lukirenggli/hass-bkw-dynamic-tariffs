"""Strict price threshold comparisons; gaps are unavailable, not off."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.util import dt as dt_util
from .const import CONF_HIGH, CONF_LOW, PRICE_UNIT
from .entity import BkwEntity
from .price import current_slot

async def async_setup_entry(hass,entry,async_add_entities) -> None:
    async_add_entities([BkwThresholdSensor(entry.runtime_data,"above_high"),
                        BkwThresholdSensor(entry.runtime_data,"below_low")])

class BkwThresholdSensor(BkwEntity,BinarySensorEntity):
    def __init__(self,coordinator,key:str) -> None:
        super().__init__(coordinator,key)
        self.key = key
        self._attr_icon = "mdi:trending-up" if key == "above_high" else "mdi:trending-down"
    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return data is not None and current_slot(data.slots,dt_util.utcnow()) is not None
    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        slot = current_slot(data.slots,dt_util.utcnow()) if data else None
        if slot is None:
            return None
        if self.key == "above_high":
            return slot.price > self.coordinator.threshold(CONF_HIGH)
        return slot.price < self.coordinator.threshold(CONF_LOW)
    @property
    def extra_state_attributes(self):
        key = CONF_HIGH if self.key == "above_high" else CONF_LOW
        return {"threshold":self.coordinator.threshold(key),"price_unit":PRICE_UNIT,
                "comparison":">" if key == CONF_HIGH else "<"}
