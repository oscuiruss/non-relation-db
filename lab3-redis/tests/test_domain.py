import unittest
from decimal import Decimal

from app.domain import effective_rate, is_in_rollout, personalize


class DomainTests(unittest.TestCase):
    def test_rollout_is_deterministic_and_boundaries_work(self):
        self.assertEqual(is_in_rollout(42, 7, 35), is_in_rollout(42, 7, 35))
        self.assertFalse(is_in_rollout(42, 7, 0))
        self.assertTrue(is_in_rollout(42, 7, 100))

    def test_profile_changes_effective_rate(self):
        gold = {"tier": "gold", "history_days": 500, "fraud_score": Decimal("0.1")}
        risky = {"tier": "bronze", "history_days": 30, "fraud_score": Decimal("0.6")}
        self.assertEqual(effective_rate(gold, Decimal("10")), Decimal("13.20"))
        self.assertEqual(effective_rate(risky, Decimal("10")), Decimal("4.00"))

    def test_exhausted_limit_returns_zero_rate(self):
        user = {
            "id": 1,
            "tier": "gold",
            "history_days": 500,
            "fraud_score": Decimal("0.1"),
        }
        offer = {
            "id": 1,
            "name": "Test",
            "category": "all",
            "cashback_percent": Decimal("10"),
            "rollout_percent": 100,
            "cashback_limit": Decimal("100"),
            "target_tiers": ["gold"],
            "min_history_days": 0,
            "max_fraud_score": Decimal("1"),
        }
        result = personalize(user, [offer], {1: Decimal("100")})
        self.assertEqual(result[0]["cashback_percent"], 0.0)
        self.assertFalse(result[0]["available"])


if __name__ == "__main__":
    unittest.main()
