"""Published-future tariffs, complete-day planning and screenshot inventory."""
from datetime import datetime, timedelta, timezone
import unittest
from loader import load
p=load('price'); descriptions=load('descriptions')
NOW=datetime(2026,11,26,10,tzinfo=timezone.utc)

def schedule(now=NOW, offset=0):
    start,end=p.day_bounds(now,offset)
    return tuple(p.PriceSlot(start+timedelta(minutes=15*i),start+timedelta(minutes=15*(i+1)),
                             0.02 if 8 <= i < 24 else (0.30 if 64 <= i < 80 else 0.10))
                 for i in range(int((end-start).total_seconds()/900)))

class PlanningTests(unittest.TestCase):
    def test_exact_screenshot_inventory(self):
        self.assertEqual(len(descriptions.SENSORS),16)
        self.assertEqual(len(descriptions.BINARY_SENSORS),12)
        all_descriptions=descriptions.SENSORS+descriptions.BINARY_SENSORS
        self.assertEqual(len({d.key for d in all_descriptions}),28)
        self.assertEqual(sum(not d.enabled for d in all_descriptions),17)
        expected_disabled={"average_tomorrow","cheap_2h_today","cheap_2h_tomorrow","cheap_4h_today",
            "expensive_2h_today","expensive_2h_tomorrow","expensive_4h_today","expensive_4h_tomorrow",
            "in_cheap_2h_today","in_expensive_2h_today","in_expensive_4h_today",
            *(f"{m}_{q}_today" for m in ('cheap','expensive') for q in (10,25,50))}
        self.assertEqual({d.key for d in all_descriptions if not d.enabled},expected_disabled)
    def test_first_image_and_forecast_are_enabled(self):
        enabled={d.key for d in descriptions.SENSORS+descriptions.BINARY_SENSORS if d.enabled}
        self.assertTrue({'cheap_4h_tomorrow','in_cheap_4h_today','forecast'} <= enabled)
    def test_cheapest_four_hours(self):
        slots=schedule(); start,_=p.day_bounds(NOW)
        w=p.extreme_window(slots,NOW,4,'cheap')
        self.assertEqual(w.start,start+timedelta(hours=2))
        self.assertEqual(w.end,start+timedelta(hours=6))
        self.assertAlmostEqual(w.average,0.02)
    def test_expensive_four_hours(self):
        slots=schedule(); start,_=p.day_bounds(NOW)
        w=p.extreme_window(slots,NOW,4,'expensive')
        self.assertEqual(w.start,start+timedelta(hours=16))
        self.assertAlmostEqual(w.average,0.30)
    def test_two_hour_tie_selects_earliest(self):
        slots=schedule(); start,_=p.day_bounds(NOW)
        w=p.extreme_window(slots,NOW,2,'cheap')
        self.assertEqual(w.start,start+timedelta(hours=2))
    def test_window_end_exclusive(self):
        w=p.extreme_window(schedule(),NOW,4,'cheap')
        self.assertFalse(p.in_window(w,w.start-timedelta(seconds=1)))
        self.assertTrue(p.in_window(w,w.start))
        self.assertTrue(p.in_window(w,w.end-timedelta(seconds=1)))
        self.assertFalse(p.in_window(w,w.end))
    def test_unknown_membership_not_false(self):
        self.assertIsNone(p.in_window(None,NOW))
    def test_incomplete_day_does_not_claim_cheapest(self):
        slots=schedule()
        for mode in ('cheap','expensive'):
            self.assertIsNone(p.extreme_window(slots[:20]+slots[21:],NOW,2,mode))
    def test_tomorrow_does_not_use_today(self):
        self.assertIsNone(p.extreme_window(schedule(),NOW,4,'cheap',1))
    def test_tomorrow_with_two_days(self):
        slots=schedule()+schedule(offset=1)
        w=p.extreme_window(slots,NOW,4,'cheap',1)
        self.assertEqual(w.start,p.day_bounds(NOW,1)[0]+timedelta(hours=2))
    def test_weighted_window_can_start_away_from_slot_start(self):
        start,end=p.day_bounds(NOW)
        slots=(p.PriceSlot(start,start+timedelta(hours=3),10),
               p.PriceSlot(start+timedelta(hours=3),start+timedelta(hours=4),0),
               p.PriceSlot(start+timedelta(hours=4),end,20))
        w=p.extreme_window(slots,NOW,2,'cheap')
        self.assertEqual(w.start,start+timedelta(hours=2))
        self.assertAlmostEqual(w.average,5)
    def test_dst_windows_have_exact_elapsed_duration(self):
        for now in (datetime(2026,3,29,12,tzinfo=timezone.utc),datetime(2026,10,25,12,tzinfo=timezone.utc)):
            w=p.extreme_window(schedule(now),now,4,'cheap')
            self.assertEqual(w.end-w.start,timedelta(hours=4))
    def test_percentile_ties_included(self):
        group=p.ranked_slots(schedule(),NOW,0.10,'cheap')
        self.assertEqual(group['selected_slots'],16)
        self.assertEqual(group['threshold'],0.02)
        self.assertGreater(group['actual_percent'],10)
    def test_expensive_percentile(self):
        group=p.ranked_slots(schedule(),NOW,0.10,'expensive')
        self.assertEqual(group['threshold'],0.30)
        self.assertEqual(group['selected_slots'],16)
    def test_rankings_monotonic(self):
        for mode in ('cheap','expensive'):
            groups=[set(p.ranked_slots(schedule(),NOW,q,mode)['slots']) for q in (.10,.25,.50)]
            self.assertTrue(groups[0] <= groups[1] <= groups[2])
    def test_rankings_need_complete_day(self):
        self.assertIsNone(p.ranked_slots(schedule()[:-1],NOW,.10,'cheap'))
    def test_forecast_excludes_active_interval(self):
        slots=schedule()+schedule(offset=1)
        snapshot=p.build_snapshot(slots,NOW)
        self.assertTrue(all(s.start > NOW for s in snapshot['forecast']))
        self.assertEqual(snapshot['next_tariff'].start,NOW+timedelta(minutes=15))
    def test_forecast_retains_published_prices(self):
        slots=schedule(); snapshot=p.build_snapshot(slots,NOW)
        self.assertEqual(snapshot['forecast'],tuple(s for s in slots if s.start > NOW))
    def test_no_future_price_is_unavailable(self):
        self.assertIsNone(p.build_snapshot(schedule(),p.day_bounds(NOW)[1])['next_tariff'])
    def test_forecast_gaps_not_filled(self):
        slots=schedule(); truncated=slots[:60]+slots[61:]
        future=p.build_snapshot(truncated,NOW)['forecast']
        self.assertTrue(any(a.end != b.start for a,b in zip(future,future[1:])))
    def test_snapshot_time_changes_current_and_countdown(self):
        slots=schedule(); start,_=p.day_bounds(NOW)
        before=p.build_snapshot(slots,start+timedelta(hours=1,minutes=59))
        after=p.build_snapshot(slots,start+timedelta(hours=2))
        self.assertEqual(before['minutes_to_change'],1)
        self.assertEqual(before['current'].price,0.10)
        self.assertEqual(after['current'].price,0.02)
        self.assertEqual(after['minutes_to_change'],240)
    def test_snapshot_rolls_to_tomorrow_at_midnight(self):
        slots=schedule()+schedule(offset=1); midnight=p.day_bounds(NOW)[1]
        snap=p.build_snapshot(slots,midnight)
        self.assertEqual(snap['today']['stats']['date'],'2026-11-27')
        self.assertEqual(snap['tomorrow']['stats']['date'],'2026-11-28')
    def test_cache_reused_without_freezing_current_price(self):
        a=p.build_snapshot(schedule(),NOW); b=p.build_snapshot(schedule(),NOW+timedelta(minutes=1))
        self.assertIs(a['today'],b['today'])
        self.assertNotEqual(a['evaluated_at'],b['evaluated_at'])
