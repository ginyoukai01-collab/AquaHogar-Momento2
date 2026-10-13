import unittest
from datetime import datetime, timedelta, timezone

from backend.services.analytics import (
    daily_consumption_anomaly,
    possible_continuous_flow,
    summarize_readings,
)


class AnalyticsTests(unittest.TestCase):
    def test_daily_anomaly_medium(self):
        self.assertEqual(daily_consumption_anomaly(370, 300, 310, 20), "media")

    def test_daily_anomaly_high(self):
        self.assertEqual(daily_consumption_anomaly(430, 300, 310, 20), "alta")

    def test_no_anomaly(self):
        self.assertIsNone(daily_consumption_anomaly(330, 300, 310, 20))

    def test_continuous_flow(self):
        now = datetime.now(timezone.utc)
        rows = [
            {"recorded_at": now - timedelta(minutes=30), "flow_l_min": 0.5},
            {"recorded_at": now - timedelta(minutes=15), "flow_l_min": 0.6},
            {"recorded_at": now, "flow_l_min": 0.5},
        ]
        self.assertTrue(possible_continuous_flow(rows, 0.3, 30))

    def test_continuous_flow_rejects_interruption(self):
        now = datetime.now(timezone.utc)
        rows = [
            {"recorded_at": now - timedelta(minutes=30), "flow_l_min": 0.5},
            {"recorded_at": now - timedelta(minutes=15), "flow_l_min": 0.0},
            {"recorded_at": now, "flow_l_min": 0.5},
        ]
        self.assertFalse(possible_continuous_flow(rows, 0.3, 30))

    def test_summary(self):
        base = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
        rows = [
            {"recorded_at": base, "volume_liters": 100},
            {"recorded_at": base + timedelta(hours=1), "volume_liters": 50},
            {"recorded_at": base + timedelta(days=1), "volume_liters": 200},
        ]
        result = summarize_readings(rows, 310)
        self.assertEqual(result["today"], 200.0)
        self.assertEqual(result["week"], 350.0)


if __name__ == "__main__":
    unittest.main()
