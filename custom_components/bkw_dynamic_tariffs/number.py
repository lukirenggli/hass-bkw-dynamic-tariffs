"""Persistent price threshold number controls."""
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.exceptions import ServiceValidationError
from .const import CONF_HIGH, CONF_LOW, MAX_THRESHOLD, MIN_THRESHOLD, PRICE_UNIT
from .entity import BkwEntity

async def async_setup_entry(hass,entry,async_add_entities) -> None:
    async_add_entities([BkwThresholdNumber(entry.runtime_data,CONF_HIGH),
                        BkwThresholdNumber(entry.runtime_data,CONF_LOW)])

class BkwThresholdNumber(BkwEntity,NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = PRICE_UNIT
    _attr_native_min_value = MIN_THRESHOLD
    _attr_native_max_value = MAX_THRESHOLD
    _attr_native_step = 0.001
    _attr_mode = NumberMode.BOX
    def __init__(self,coordinator,key:str) -> None:
        super().__init__(coordinator,key)
        self.key = key
        self._attr_icon = "mdi:arrow-collapse-up" if key == CONF_HIGH else "mdi:arrow-collapse-down"
    @property
    def available(self) -> bool:
        return True
    @property
    def native_value(self) -> float:
        return self.coordinator.threshold(self.key)
    async def async_set_native_value(self,value:float) -> None:
        try:
            self.coordinator.set_threshold(self.key,value)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
