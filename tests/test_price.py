"""Regression tests for real schema semantics, boundaries, missing data and DST."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest
from loader import load
p = load("price")
UTC = timezone.utc
NOW = datetime(2026,11,26,10,tzinfo=UTC)

def row(start,end,value=0.05,unit="CHF_kWh"):
    return {"start_timestamp":start.isoformat(),"end_timestamp":end.isoformat(),
            "feed_in":[{"unit":unit,"value":value}]}

def payload(rows):
    return {"publication_timestamp":NOW.isoformat(),"prices":rows}

def day_slots(now,price=0.05):
    start,end = p.day_bounds(now)
    slots = []
    while start < end:
        following = min(start+timedelta(minutes=15),end)
        slots.append(p.PriceSlot(start,following,price))
        start = following
    return tuple(slots)

class PriceTests(unittest.TestCase):
    def test_documented_schema_and_utc(self):
        data = p.parse_tariffs(payload([row(NOW,NOW+timedelta(minutes=15))]),NOW)
        self.assertEqual(data.slots[0].price,0.05)
        self.assertEqual(data.slots[0].start.tzinfo,UTC)
    def test_negative_and_zero_prices(self):
        for value in (-0.04,0):
            data = p.parse_tariffs(payload([row(NOW,NOW+timedelta(minutes=15),value)]),NOW)
            self.assertEqual(data.slots[0].price,value)
    def test_all_feed_in_components_are_summed(self):
        r = row(NOW,NOW+timedelta(hours=1),0.04)
        r['feed_in'].append({'unit':'CHF_kWh','value':0.02})
        self.assertAlmostEqual(p.parse_tariffs(payload([r]),NOW).slots[0].price,0.06)
    def test_unsupported_units_rejected(self):
        with self.assertRaises(p.InvalidTariffs):
            p.parse_tariffs(payload([row(NOW,NOW+timedelta(hours=1),unit='Rp_kWh')]),NOW)
    def test_non_numeric_prices_rejected(self):
        for value in (True,None,'0.05',float('nan'),float('inf')):
            with self.subTest(value=value),self.assertRaises(p.InvalidTariffs):
                p.parse_tariffs(payload([row(NOW,NOW+timedelta(hours=1),value)]),NOW)
    def test_empty_payload_rejected(self):
        for value in ({},None,[],payload([]),{'publication_timestamp':NOW.isoformat(),'prices':None}):
            with self.assertRaises(p.InvalidTariffs): p.parse_tariffs(value,NOW)
    def test_missing_feed_in_rejected(self):
        r = row(NOW,NOW+timedelta(hours=1)); del r['feed_in']
        with self.assertRaises(p.InvalidTariffs): p.parse_tariffs(payload([r]),NOW)
    def test_naive_timestamp_rejected(self):
        with self.assertRaises(p.InvalidTariffs): p.parse_timestamp('2026-11-26T10:00:00')
    def test_bad_timestamp_rejected(self):
        with self.assertRaises(p.InvalidTariffs): p.parse_timestamp('invalid')
    def test_zero_negative_duration_rejected(self):
        for end in (NOW,NOW-timedelta(minutes=1)):
            with self.assertRaises(p.InvalidTariffs): p.parse_tariffs(payload([row(NOW,end)]),NOW)
    def test_duplicate_and_overlap_rejected(self):
        r = row(NOW,NOW+timedelta(hours=1))
        with self.assertRaises(p.InvalidTariffs): p.parse_tariffs(payload([r,r]),NOW)
        with self.assertRaises(p.InvalidTariffs):
            p.parse_tariffs(payload([r,row(NOW+timedelta(minutes=15),NOW+timedelta(hours=2))]),NOW)
    def test_unsorted_intervals_are_sorted(self):
        data = p.parse_tariffs(payload([row(NOW+timedelta(hours=1),NOW+timedelta(hours=2)),
                                      row(NOW,NOW+timedelta(hours=1))]),NOW)
        self.assertEqual(data.slots[0].start,NOW)
    def test_start_inclusive_end_exclusive(self):
        a=p.PriceSlot(NOW,NOW+timedelta(minutes=15),0.05)
        b=p.PriceSlot(a.end,a.end+timedelta(minutes=15),0.15)
        self.assertEqual(p.current_slot((a,b),NOW),a)
        self.assertEqual(p.current_slot((a,b),a.end),b)
        self.assertIsNone(p.current_slot((a,b),b.end))
    def test_actual_change_skips_equal_prices(self):
        a=p.PriceSlot(NOW,NOW+timedelta(minutes=15),0.05)
        b=p.PriceSlot(a.end,a.end+timedelta(minutes=15),0.05)
        c=p.PriceSlot(b.end,b.end+timedelta(minutes=15),0.10)
        self.assertEqual(p.next_change((a,b,c),NOW),c.start)
        self.assertEqual(p.minutes_to_change((a,b,c),NOW),30)
    def test_countdown_rounds_up(self):
        a=p.PriceSlot(NOW,NOW+timedelta(seconds=30),0.05)
        b=p.PriceSlot(a.end,a.end+timedelta(minutes=15),0.10)
        self.assertEqual(p.minutes_to_change((a,b),NOW),1)
    def test_unknown_change_at_end(self):
        self.assertIsNone(p.next_change((p.PriceSlot(NOW,NOW+timedelta(hours=1),0.05),),NOW))
    def test_gap_is_not_a_price_change(self):
        a=p.PriceSlot(NOW,NOW+timedelta(minutes=15),0.05)
        b=p.PriceSlot(NOW+timedelta(minutes=30),NOW+timedelta(hours=1),0.1)
        self.assertIsNone(p.next_change((a,b),NOW))
        self.assertIsNone(p.current_slot((a,b),NOW+timedelta(minutes=20)))
    def test_full_day_statistics(self):
        stats=p.daily_statistics(day_slots(NOW),NOW)
        self.assertTrue(stats['complete'])
        self.assertEqual(stats['coverage_percent'],100)
        self.assertEqual(stats['slots_count'],96)
        self.assertAlmostEqual(stats['average'],0.05)
    def test_duration_weighted_average(self):
        start,end=p.day_bounds(NOW)
        slots=(p.PriceSlot(start,start+timedelta(hours=1),0.24),
               p.PriceSlot(start+timedelta(hours=1),end,0.0))
        stats=p.daily_statistics(slots,NOW)
        self.assertAlmostEqual(stats['average'],0.01)
        self.assertEqual(stats['minimum'],0)
        self.assertEqual(stats['maximum'],0.24)
    def test_gap_daily_stats_are_unavailable(self):
        slots=day_slots(NOW)
        stats=p.daily_statistics(slots[:10]+slots[11:],NOW)
        self.assertFalse(stats['complete'])
        self.assertLess(stats['coverage_percent'],100)
        for key in ('average','minimum','maximum'): self.assertIsNone(stats[key])
    def test_missing_today(self):
        stats=p.daily_statistics((),NOW)
        self.assertFalse(stats['complete']); self.assertEqual(stats['coverage_percent'],0)
    def test_spring_dst_23_hours(self):
        now=datetime(2026,3,29,12,tzinfo=UTC)
        stats=p.daily_statistics(day_slots(now),now)
        self.assertEqual(stats['expected_minutes'],1380)
        self.assertEqual(stats['slots_count'],92); self.assertTrue(stats['complete'])
    def test_autumn_dst_25_hours(self):
        now=datetime(2026,10,25,12,tzinfo=UTC)
        stats=p.daily_statistics(day_slots(now),now)
        self.assertEqual(stats['expected_minutes'],1500)
        self.assertEqual(stats['slots_count'],100); self.assertTrue(stats['complete'])
    def test_swiss_day_not_utc_day(self):
        self.assertEqual(p.day_bounds(NOW)[0],datetime(2026,11,25,23,tzinfo=UTC))
    def test_midnight_rollover(self):
        today=day_slots(NOW,0.05); tomorrow=day_slots(NOW+timedelta(days=1),0.1)
        now=p.day_bounds(NOW)[1]
        self.assertAlmostEqual(p.daily_statistics(today+tomorrow,now)['average'],0.1)
    def test_intervals_clipped_to_day(self):
        start,end=p.day_bounds(NOW)
        stats=p.daily_statistics((p.PriceSlot(start-timedelta(hours=1),end+timedelta(hours=1),0.2),),NOW)
        self.assertTrue(stats['complete']); self.assertAlmostEqual(stats['average'],0.2)
    def test_merge_retains_today_when_api_returns_tomorrow(self):
        old=p.TariffData(day_slots(NOW),NOW,NOW)
        new=p.TariffData(day_slots(NOW+timedelta(days=1),0.1),NOW+timedelta(hours=1),NOW)
        merged=p.merge_tariffs(old,new,NOW)
        self.assertEqual(len(merged.slots),192)
        self.assertAlmostEqual(p.daily_statistics(merged.slots,NOW)['average'],0.05)
    def test_merge_does_not_resurrect_missing_intervals(self):
        slots=day_slots(NOW)
        old=p.TariffData(slots,NOW,NOW)
        new=p.TariffData(slots[:10]+slots[11:],NOW,NOW)
        self.assertEqual(len(p.merge_tariffs(old,new,NOW).slots),95)
    def test_merge_prunes_past_days(self):
        old=p.TariffData(day_slots(NOW-timedelta(days=1))+day_slots(NOW),NOW,NOW)
        new=p.TariffData(day_slots(NOW),NOW,NOW)
        self.assertEqual(len(p.merge_tariffs(old,new,NOW).slots),96)
    def test_regressed_publication_rejected(self):
        old=p.TariffData(day_slots(NOW),NOW,NOW)
        new=p.TariffData(day_slots(NOW),NOW-timedelta(hours=1),NOW)
        with self.assertRaises(p.InvalidTariffs): p.merge_tariffs(old,new,NOW)

if __name__ == '__main__': unittest.main()
