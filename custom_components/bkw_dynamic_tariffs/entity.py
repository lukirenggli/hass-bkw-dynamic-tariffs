"""Stable shared device and entity identifiers."""
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import API_URL, DOMAIN, NAME
from .coordinator import BkwCoordinator

class BkwEntity(CoordinatorEntity[BkwCoordinator]):
    _attr_has_entity_name = True
    def __init__(self,coordinator:BkwCoordinator,key:str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN,coordinator.entry.entry_id)},
            name=NAME,manufacturer="BKW Energie AG",model="Dynamic feed-in remuneration",
            entry_type=DeviceEntryType.SERVICE,configuration_url=API_URL)
