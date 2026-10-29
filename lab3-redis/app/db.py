from __future__ import annotations

from decimal import Decimal
import asyncpg

from .domain import personalize


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    tier TEXT NOT NULL CHECK (tier IN ('bronze', 'silver', 'gold')),
    history_days INTEGER NOT NULL CHECK (history_days >= 0),
    fraud_score NUMERIC(5,4) NOT NULL CHECK (fraud_score BETWEEN 0 AND 1),
    total_spent NUMERIC(14,2) NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS offers (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    cashback_percent NUMERIC(5,2) NOT NULL CHECK (cashback_percent >= 0),
    rollout_percent INTEGER NOT NULL CHECK (rollout_percent BETWEEN 0 AND 100),
    active_from TIMESTAMPTZ NOT NULL,
    active_to TIMESTAMPTZ NOT NULL,
    cashback_limit NUMERIC(14,2) NOT NULL CHECK (cashback_limit >= 0),
    target_tiers TEXT[] NOT NULL,
    min_history_days INTEGER NOT NULL DEFAULT 0,
    max_fraud_score NUMERIC(5,4) NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS user_offer_usage (
    user_id BIGINT NOT NULL REFERENCES users(id),
    offer_id BIGINT NOT NULL REFERENCES offers(id),
    cashback_used NUMERIC(14,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, offer_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    offer_id BIGINT REFERENCES offers(id),
    category TEXT NOT NULL,
    amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    cashback NUMERIC(14,2) NOT NULL CHECK (cashback >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS transactions_user_created_idx
    ON transactions (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS offers_active_idx ON offers (active_from, active_to);
"""


SEED = """
INSERT INTO users (id, tier, history_days, fraud_score, total_spent)
SELECT i,
       (ARRAY['bronze', 'silver', 'gold'])[1 + (i % 3)],
       30 + (i * 17 % 900),
       ((i * 37 % 70)::numeric / 100),
       (i * 73 % 200000)::numeric / 10
FROM generate_series(1, 1000) AS i
ON CONFLICT (id) DO NOTHING;

INSERT INTO offers (
    name, category, cashback_percent, rollout_percent, active_from, active_to,
    cashback_limit, target_tiers, min_history_days, max_fraud_score
)
SELECT * FROM (VALUES
    ('Кофе каждый день', 'cafe', 10.00, 30, now() - interval '1 day', now() + interval '30 days', 1000.00, ARRAY['bronze','silver','gold'], 30, 0.60),
    ('Такси для постоянных клиентов', 'taxi', 7.00, 50, now() - interval '1 day', now() + interval '14 days', 700.00, ARRAY['silver','gold'], 180, 0.35),
    ('Суперкэшбэк в супермаркетах', 'grocery', 15.00, 10, now() - interval '1 day', now() + interval '7 days', 1500.00, ARRAY['gold'], 365, 0.20),
    ('Кэшбэк на всё', 'all', 2.00, 100, now() - interval '1 day', now() + interval '90 days', 500.00, ARRAY['bronze','silver','gold'], 0, 0.70)
) AS seed(name, category, cashback_percent, rollout_percent, active_from, active_to,
          cashback_limit, target_tiers, min_history_days, max_fraud_score)
WHERE NOT EXISTS (SELECT 1 FROM offers);
"""


async def create_pool(database_url: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(database_url, min_size=2, max_size=20)


async def initialize(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)
        await conn.execute(SEED)


async def calculate_personalization(
    conn: asyncpg.Connection, user_id: int
) -> dict:
    user_record = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    if user_record is None:
        raise KeyError(user_id)
    offer_records = await conn.fetch(
        """
        SELECT * FROM offers
        WHERE active_from <= now() AND active_to > now()
        ORDER BY id
        """
    )
    usage_records = await conn.fetch(
        "SELECT offer_id, cashback_used FROM user_offer_usage WHERE user_id = $1",
        user_id,
    )
    user = dict(user_record)
    offers = [dict(row) for row in offer_records]
    usage = {row["offer_id"]: Decimal(row["cashback_used"]) for row in usage_records}
    return {
        "user_id": user_id,
        "tier": user["tier"],
        "offers": personalize(user, offers, usage),
    }
