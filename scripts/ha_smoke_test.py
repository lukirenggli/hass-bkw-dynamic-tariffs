"""Run with real HA 2026.11.3 on GitHub; no live BKW requests."""
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import AsyncMock, patch

from homeassistant import loader
from homeassistant.bootstrap import async_load_base_functionality
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

ROOT=Path(__file__).resolve().parents[1]
DOMAIN='bkw_dynamic_tariffs'

async def main():
    with tempfile.TemporaryDirectory() as directory:
        shutil.copytree(ROOT/'custom_components',Path(directory)/'custom_components',
                        ignore=shutil.ignore_patterns('__pycache__'))
        sys.path.insert(0,directory)
        hass=HomeAssistant(directory)
        hass.config_entries=ConfigEntries(hass,{})
        try:
            # HomeAssistant() alone does not initialize the integration loader.
            # Follow HA's bootstrap ordering before setting up any component:
            # loader caches, then registries/helpers/config-entry storage.
            loader.async_setup(hass)  # Synchronous callback, despite its name.
            assert await async_load_base_functionality(hass), 'HA base initialization failed'
            assert await async_setup_component(hass,'homeassistant',{})
            from custom_components.bkw_dynamic_tariffs.api import BkwApi, BkwApiError
            from custom_components.bkw_dynamic_tariffs.price import PriceSlot, TariffData, day_bounds
            from custom_components.bkw_dynamic_tariffs.const import CONF_HIGH, CONF_LOW
            now=datetime.now(timezone.utc)
            start,end=day_bounds(now)
            slots=tuple(PriceSlot(start+timedelta(minutes=15*i),start+timedelta(minutes=15*(i+1)),
                                 0.04 if i%2==0 else 0.20)
                        for i in range(int((end-start).total_seconds()/900)))
            # Publish tomorrow as well, allowing tomorrow's optional windows to load.
            tomorrow_start,tomorrow_end=day_bounds(end)
            tomorrow_slots=tuple(PriceSlot(tomorrow_start+timedelta(minutes=15*i),
                                          tomorrow_start+timedelta(minutes=15*(i+1)),
                                          0.06 if i % 2 == 0 else 0.22)
                                 for i in range(int((tomorrow_end-tomorrow_start).total_seconds()/900)))
            data=TariffData(slots+tomorrow_slots,now,now)
            with patch.object(BkwApi,'async_fetch',new=AsyncMock(return_value=data)) as fetch:
                form=await hass.config_entries.flow.async_init(DOMAIN,context={'source':'user'})
                assert form['type']=='form',form
                result=await hass.config_entries.flow.async_configure(form['flow_id'],
                    {CONF_HIGH:0.15,CONF_LOW:0.05})
                assert result['type']=='create_entry',result
                entry=result['result']
                await hass.async_block_till_done()
                assert entry.state.value=='loaded',entry.state
                coordinator=entry.runtime_data
                entities=er.async_entries_for_config_entry(er.async_get(hass),entry.entry_id)
                assert len(entities)==31,[(entity.entity_id,entity.unique_id) for entity in entities]
                assert sum(entity.disabled_by is None for entity in entities)==14
                assert sum(entity.disabled_by is not None for entity in entities)==17
                ids={entity.unique_id.rsplit(entry.entry_id+'_',1)[-1]:entity.entity_id for entity in entities}
                assert hass.states.get(ids['current_price']).state not in ('unknown','unavailable')
                assert hass.states.get(ids['forecast']).state not in ('unknown','unavailable')
                assert hass.states.get(ids['forecast']).attributes['forecast_count'] > 0
                assert hass.states.get(ids['cheap_4h_tomorrow']).state not in ('unknown','unavailable')
                assert hass.states.get(ids['average_tomorrow']) is None
                before=fetch.call_count
                await hass.services.async_call('number','set_value',
                    {'entity_id':ids[CONF_HIGH],'value':0.25},blocking=True)
                assert coordinator.threshold(CONF_HIGH)==0.25
                await hass.async_block_till_done()
                assert fetch.call_count==before,'Changing thresholds fetched tariffs'
                coordinator._tick(now)
                assert fetch.call_count==before,'Local clock fetched tariffs'
                assert coordinator.update_interval==timedelta(hours=12)
                options=await hass.config_entries.options.async_init(entry.entry_id)
                assert options['type']=='form'
                await hass.config_entries.options.async_configure(options['flow_id'],
                    {CONF_HIGH:0.30,CONF_LOW:-0.05})
                await hass.async_block_till_done()
                assert coordinator.threshold(CONF_LOW)==-0.05
                assert fetch.call_count==before,'Options fetched tariffs'
                # Enable all optional entities and explicitly reload (without waiting
                # for the entity registry's delayed automatic reload).
                registry=er.async_get(hass)
                for entity in entities:
                    if entity.disabled_by is not None:
                        registry.async_update_entity(entity.entity_id,disabled_by=None)
                assert await hass.config_entries.async_reload(entry.entry_id)
                await hass.async_block_till_done()
                coordinator=entry.runtime_data
                assert hass.states.get(ids['average_tomorrow']).state not in ('unknown','unavailable')
                for key in ('cheap_2h_today','expensive_4h_today','cheap_10_today','in_expensive_2h_today'):
                    assert hass.states.get(ids[key]).state not in ('unknown','unavailable'),key
                before=fetch.call_count
                # Direct refresh avoids waiting for the debouncer in a test.
                await coordinator.async_refresh()
                assert fetch.call_count==before+1
                with patch.object(BkwApi,'async_fetch',new=AsyncMock(side_effect=BkwApiError('offline'))):
                    await coordinator.async_refresh()
                    assert not coordinator.last_update_success
                    assert hass.states.get(ids['current_price']).state not in ('unknown','unavailable')
                    assert hass.states.get(ids['refresh_tariffs']).state!='unavailable'
                assert await hass.config_entries.async_unload(entry.entry_id)
                assert coordinator._cancel_tick is None,'Local timer not stopped'
                print('PASS: real HA flow, 31 registered/14 default-active entities, optional activation, thresholds/options, local clock, refresh, cache and unload')
        finally:
            await hass.async_stop()
            sys.path.remove(directory)

if __name__=='__main__': asyncio.run(main())
