"""UI setup and options; one public BKW feed-in tariff."""
from math import isfinite
from typing import Any
import probatio
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode
from .api import BkwApi, BkwApiError
from .const import (CONF_HIGH, CONF_LOW, DEFAULT_HIGH, DEFAULT_LOW, DOMAIN,
                    MAX_THRESHOLD, MIN_THRESHOLD, NAME, PRICE_UNIT)

def threshold_schema(values: dict[str, Any]) -> probatio.Schema:
    selector = NumberSelector(NumberSelectorConfig(min=MIN_THRESHOLD,max=MAX_THRESHOLD,
        step=0.001,mode=NumberSelectorMode.BOX,unit_of_measurement=PRICE_UNIT))
    return probatio.Schema({probatio.Required(CONF_HIGH,default=values.get(CONF_HIGH,DEFAULT_HIGH)):selector,
                       probatio.Required(CONF_LOW,default=values.get(CONF_LOW,DEFAULT_LOW)):selector})

def valid_thresholds(values: dict[str, Any]) -> bool:
    low,high = values[CONF_LOW],values[CONF_HIGH]
    return (all(not isinstance(v,bool) and isfinite(v) and MIN_THRESHOLD <= v <= MAX_THRESHOLD
                for v in (low,high)) and low <= high)

class BkwConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return BkwOptionsFlow()

    async def async_step_user(self,user_input: dict[str,Any] | None = None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors = {}
        if user_input is not None:
            if not valid_thresholds(user_input):
                errors["base"] = "invalid_thresholds"
            else:
                try:
                    await BkwApi(async_get_clientsession(self.hass)).async_fetch()
                except BkwApiError:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(title=NAME,data=user_input)
        return self.async_show_form(step_id="user",data_schema=threshold_schema(user_input or {}),errors=errors)

class BkwOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self,user_input: dict[str,Any] | None = None):
        errors = {}
        if user_input is not None:
            if valid_thresholds(user_input):
                return self.async_create_entry(title="",data=user_input)
            errors["base"] = "invalid_thresholds"
        values = {**self.config_entry.data,**self.config_entry.options}
        return self.async_show_form(step_id="init",data_schema=threshold_schema(user_input or values),errors=errors)
