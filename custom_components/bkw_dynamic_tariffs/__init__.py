"""BKW Dynamic Tariffs integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import BkwApi
from .coordinator import BkwCoordinator
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = BkwCoordinator(hass,entry,BkwApi(async_get_clientsession(hass)))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry,PLATFORMS)
    coordinator.start_clock()
    entry.async_on_unload(coordinator.stop_clock)
    entry.async_on_unload(entry.add_update_listener(async_options_updated))
    return True

async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    entry.runtime_data.async_update_listeners()

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry,PLATFORMS)
