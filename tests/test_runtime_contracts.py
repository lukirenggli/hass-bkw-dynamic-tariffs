"""Actual integration methods with minimal mocked host interfaces, NOT a real-HA test.

The independent real-HA CI smoke test remains mandatory before a release.
"""
from datetime import datetime, timedelta, timezone
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from loader import load
p=load('price'); desc=load('descriptions')
NOW=datetime(2026,11,26,10,tzinfo=timezone.utc)
clock={'now':NOW}; timers=[]

def mod(name,**attrs):
    m=types.ModuleType(name)
    for k,v in attrs.items(): setattr(m,k,v)
    return m
class Generic:
    @classmethod
    def __class_getitem__(cls,key): return cls
class Coordinator(Generic):
    def __init__(self,hass,logger,**kwargs):
        self.hass=hass; self.data=None; self.last_update_success=True
        self.update_interval=kwargs['update_interval']; self.notifications=0
    def async_update_listeners(self): self.notifications+=1
    async def async_request_refresh(self): pass
class Entity(Generic):
    def __init__(self,coordinator): self.coordinator=coordinator
class HostSensor: pass
class HostBinary: pass
class HostButton: pass

def track(hass,callback,when):
    item={'callback':callback,'when':when,'active':True}; timers.append(item)
    def cancel(): item['active']=False
    return cancel
fake_modules={
 'homeassistant':mod('homeassistant'),
 'homeassistant.config_entries':mod('homeassistant.config_entries',ConfigEntry=object),
 'homeassistant.core':mod('homeassistant.core',CALLBACK_TYPE=object,HomeAssistant=object,callback=lambda f:f),
 'homeassistant.helpers':mod('homeassistant.helpers'),
 'homeassistant.helpers.event':mod('homeassistant.helpers.event',async_track_point_in_utc_time=track),
 'homeassistant.helpers.update_coordinator':mod('homeassistant.helpers.update_coordinator',DataUpdateCoordinator=Coordinator,UpdateFailed=ValueError,CoordinatorEntity=Entity),
 'homeassistant.helpers.device_registry':mod('homeassistant.helpers.device_registry',DeviceEntryType=types.SimpleNamespace(SERVICE='service'),DeviceInfo=lambda **kw:kw),
 'homeassistant.util':mod('homeassistant.util',dt=types.SimpleNamespace(utcnow=lambda:clock['now'])),
 'homeassistant.const':mod('homeassistant.const',EntityCategory=types.SimpleNamespace(DIAGNOSTIC='diagnostic',CONFIG='config'),UnitOfTime=types.SimpleNamespace(MINUTES='min')),
 'homeassistant.components':mod('homeassistant.components'),
 'homeassistant.components.sensor':mod('homeassistant.components.sensor',SensorEntity=HostSensor,SensorDeviceClass=types.SimpleNamespace(TIMESTAMP='timestamp',DURATION='duration'),SensorStateClass=types.SimpleNamespace(MEASUREMENT='measurement')),
 'homeassistant.components.binary_sensor':mod('homeassistant.components.binary_sensor',BinarySensorEntity=HostBinary),
 'homeassistant.components.button':mod('homeassistant.components.button',ButtonEntity=HostButton),
}
with patch.dict('sys.modules',fake_modules):
    co=load('coordinator'); sensor=load('sensor'); binary=load('binary_sensor'); button=load('button')

def day_data():
    start,end=p.day_bounds(NOW)
    slots=tuple(p.PriceSlot(start+timedelta(minutes=15*i),start+timedelta(minutes=15*(i+1)),
                 0.02 if 8 <= i < 24 else 0.10) for i in range(96))
    return p.TariffData(slots,NOW,NOW)

def coordinator():
    clock['now']=NOW; timers.clear()
    entry=types.SimpleNamespace(entry_id='test',data={'high_threshold':0.15,'low_threshold':0.05},options={})
    hass=MagicMock()
    def update(entry,options): entry.options=options
    hass.config_entries.async_update_entry.side_effect=update
    result=co.BkwCoordinator(hass,entry,types.SimpleNamespace(async_fetch=AsyncMock(return_value=day_data())))
    result.data=day_data();result._async_refresh_finished()
    return result

def sensor_by_key(c,key):
    return sensor.BkwSensor(c,next(d for d in desc.SENSORS if d.key==key))
def binary_by_key(c,key):
    return binary.BkwTariffBinarySensor(c,next(d for d in desc.BINARY_SENSORS if d.key==key))

class RuntimeContracts(unittest.TestCase):
    def test_local_tick_does_not_call_api(self):
        c=coordinator(); c.start_clock(); clock['now']=NOW+timedelta(minutes=1)
        c._tick(clock['now'])
        self.assertEqual(c.api.async_fetch.call_count,0)
        self.assertEqual(c.data.retrieved,NOW)
        self.assertEqual(c.local_updated_at,clock['now'])
        self.assertEqual(c.update_interval,timedelta(hours=12))
    def test_manual_tick_does_not_leave_duplicate_timers(self):
        c=coordinator(); c.start_clock(); c._tick(NOW)
        self.assertEqual(sum(t['active'] for t in timers),1)
    def test_stop_prevents_late_callback_restart(self):
        c=coordinator(); c.start_clock(); late=timers[-1]['callback']; c.stop_clock(); late(NOW)
        self.assertFalse(any(t['active'] for t in timers))
        self.assertFalse(c._clock_started)
    def test_schedules_exact_nonminute_interval_edge(self):
        c=coordinator()
        c.data=p.TariffData((p.PriceSlot(NOW,NOW+timedelta(seconds=20),.05),
                            p.PriceSlot(NOW+timedelta(seconds=20),NOW+timedelta(minutes=2),.10)),NOW,NOW)
        c._async_refresh_finished(); c.start_clock()
        self.assertEqual(timers[-1]['when'],NOW+timedelta(seconds=20))
    def test_current_and_binary_transition_together(self):
        c=coordinator(); c.start_clock(); start,_=p.day_bounds(NOW)
        c._tick(start+timedelta(hours=1,minutes=59))
        current=sensor_by_key(c,'current_price'); low=binary_by_key(c,'below_low')
        self.assertEqual(current.native_value,.10); self.assertFalse(low.is_on)
        c._tick(start+timedelta(hours=2))
        self.assertEqual(current.native_value,.02); self.assertTrue(low.is_on)
        self.assertTrue(binary_by_key(c,'in_cheap_4h_today').is_on)
    def test_window_membership_turns_off_at_end(self):
        c=coordinator(); c.start_clock(); start,_=p.day_bounds(NOW)
        c._tick(start+timedelta(hours=6))
        self.assertFalse(binary_by_key(c,'in_cheap_4h_today').is_on)
    def test_gap_does_not_report_off_or_zero(self):
        c=coordinator(); c.data=p.TariffData(tuple(s for s in c.data.slots if not s.start <= NOW < s.end),NOW,NOW)
        c._async_refresh_finished()
        self.assertIsNone(sensor_by_key(c,'current_price').native_value)
        self.assertFalse(binary_by_key(c,'below_low').available)
        self.assertIsNone(binary_by_key(c,'in_cheap_4h_today').is_on)
    def test_failed_api_keeps_valid_price(self):
        c=coordinator(); c.last_update_success=False; c._async_refresh_finished()
        self.assertTrue(sensor_by_key(c,'current_price').available)
        self.assertFalse(sensor_by_key(c,'current_price').extra_state_attributes['last_api_success'])
    def test_threshold_change_no_reload_or_api(self):
        c=coordinator(); c.set_threshold('low_threshold',.12)
        self.assertTrue(binary_by_key(c,'below_low').is_on)
        self.assertEqual(c.entry.options['low_threshold'],.12)
        c.api.async_fetch.assert_not_called()
    def test_equality_threshold_is_off(self):
        c=coordinator(); c.set_threshold('high_threshold',.10)
        self.assertFalse(binary_by_key(c,'above_high').is_on)
        c.set_threshold('low_threshold',.10)
        self.assertFalse(binary_by_key(c,'below_low').is_on)
    def test_forecast_has_original_intervals(self):
        c=coordinator(); forecast=sensor_by_key(c,'forecast')
        self.assertEqual(forecast.native_value,.10)
        self.assertEqual(forecast.extra_state_attributes['forecast_count'],51)
        self.assertFalse(forecast.extra_state_attributes['prediction_model'])
    def test_disabled_defaults_are_entity_attributes(self):
        c=coordinator()
        entities=[sensor.BkwSensor(c,d) for d in desc.SENSORS]+[binary.BkwTariffBinarySensor(c,d) for d in desc.BINARY_SENSORS]
        self.assertEqual(sum(not e._attr_entity_registry_enabled_default for e in entities),17)
    def test_diagnostic_separates_api_and_local_activity(self):
        c=coordinator(); c.start_clock(); c._tick(NOW+timedelta(minutes=1))
        diagnostic=sensor_by_key(c,'last_api_update')
        self.assertEqual(diagnostic.native_value,NOW)
        self.assertEqual(diagnostic.extra_state_attributes['local_updated_at'],(NOW+timedelta(minutes=1)).isoformat())

class AsyncRuntimeContracts(unittest.IsolatedAsyncioTestCase):
    async def test_one_fetch_per_update(self):
        c=coordinator(); await c._async_update_data()
        c.api.async_fetch.assert_awaited_once()
    async def test_button_does_not_raise_previous_failure(self):
        c=coordinator(); c.last_update_success=False; c.async_request_refresh=AsyncMock()
        await button.BkwRefreshButton(c,'refresh_tariffs').async_press()
        c.async_request_refresh.assert_awaited_once()
