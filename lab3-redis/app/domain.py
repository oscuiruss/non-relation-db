from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import hashlib
from typing import Any


MONEY = Decimal("0.01")


def is_in_rollout(user_id: int, offer_id: int, rollout_percent: int) -> bool:
    """Deterministically assign a user to an offer's rollout cohort."""
    digest = hashlib.sha256(f"{offer_id}:{user_id}".encode()).digest()
    bucket = int.from_bytes(digest[:8], "big") % 10_000
    return bucket < rollout_percent * 100


def effective_rate(user: dict[str, Any], base_rate: Decimal) -> Decimal:
    tier_factor = {
        "bronze": Decimal("0.80"),
        "silver": Decimal("1.00"),
        "gold": Decimal("1.20"),
    }.get(user["tier"], Decimal("1.00"))
    fraud = Decimal(str(user["fraud_score"]))
    fraud_factor = (
        Decimal("0.50")
        if fraud > Decimal("0.50")
        else Decimal("0.80")
        if fraud > Decimal("0.20")
        else Decimal("1.00")
    )
    history_factor = (
        Decimal("1.10") if user["history_days"] >= 365 else Decimal("1.00")
    )
    return min(
        base_rate * tier_factor * fraud_factor * history_factor,
        Decimal("30.00"),
    ).quantize(MONEY, rounding=ROUND_HALF_UP)


def personalize(
    user: dict[str, Any], offers: list[dict[str, Any]], usage: dict[int, Decimal]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for offer in offers:
        if user["tier"] not in offer["target_tiers"]:
            continue
        if user["history_days"] < offer["min_history_days"]:
            continue
        if Decimal(str(user["fraud_score"])) > Decimal(
            str(offer["max_fraud_score"])
        ):
            continue
        if not is_in_rollout(user["id"], offer["id"], offer["rollout_percent"]):
            continue

        used = usage.get(offer["id"], Decimal("0"))
        remaining = max(Decimal(str(offer["cashback_limit"])) - used, Decimal("0"))
        exhausted = remaining == 0
        rate = Decimal("0") if exhausted else effective_rate(
            user, Decimal(str(offer["cashback_percent"]))
        )
        result.append(
            {
                "offer_id": offer["id"],
                "name": offer["name"],
                "category": offer["category"],
                "cashback_percent": float(rate),
                "remaining_limit": float(remaining.quantize(MONEY)),
                "available": not exhausted,
                "reason": "limit_exhausted" if exhausted else "eligible",
            }
        )
    return sorted(result, key=lambda item: item["cashback_percent"], reverse=True)
