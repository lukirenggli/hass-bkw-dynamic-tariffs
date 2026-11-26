"""Manual debounced tariff refresh."""
from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from .entity import BkwEntity

async def async_setup_entry(hass,entry,async_add_entities) -> None:
    async_add_entities([BkwRefreshButton(entry.runtime_data,"refresh_tariffs")])

class BkwRefreshButton(BkwEntity,ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:refresh"
    @property
    def available(self) -> bool:
        return True
    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
        if not self.coordinator.last_update_success:
            raise HomeAssistantError("BKW tariff refresh failed; check integration logs")
