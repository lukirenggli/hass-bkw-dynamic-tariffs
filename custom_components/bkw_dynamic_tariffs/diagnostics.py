"""Public tariff diagnostics without household identifiers or credentials."""
from homeassistant.util import dt as dt_util
from .const import CONF_HIGH, CONF_LOW
from .price import daily_statistics

async def async_get_config_entry_diagnostics(hass,entry):
    coordinator = entry.runtime_data
    data = coordinator.data
    return {"api_success":coordinator.last_update_success,
        "last_error":str(coordinator.last_exception) if not coordinator.last_update_success else None,
        "high_threshold":coordinator.threshold(CONF_HIGH),"low_threshold":coordinator.threshold(CONF_LOW),
        "publication_timestamp":data.publication.isoformat() if data else None,
        "retrieved_at":data.retrieved.isoformat() if data else None,
        "daily_statistics":daily_statistics(data.slots,dt_util.utcnow()) if data else None,
        "prices":[s.as_dict() for s in data.slots] if data else []}
