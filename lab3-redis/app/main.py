from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal, ROUND_HALF_UP
import asyncio
import json
import random
import time
from typing import Annotated
from uuid import UUID, uuid4

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from redis.asyncio import Redis

from .config import settings
from .db import calculate_personalization, create_pool, initialize


CACHE_REQUESTS = Counter(
    "loyalty_cache_requests_total", "Cache lookups", ["result"]
)
CALCULATION_TIME = Histogram(
    "loyalty_personalization_calculation_seconds",
    "Time spent calculating personalization in PostgreSQL",
)
HTTP_REQUESTS = Counter(
    "loyalty_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
HTTP_DURATION = Histogram(
    "loyalty_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
)
TRANSACTIONS = Counter(
    "loyalty_transactions_total", "Processed transactions", ["result"]
)
CASHBACK_AWARDED = Counter(
    "loyalty_cashback_awarded_total", "Cashback awarded", ["category"]
)
IN_PROGRESS = Gauge("loyalty_http_requests_in_progress", "In-progress HTTP requests")

CATALOG_VERSION_KEY = "loyalty:catalog-version"
USER_VERSION_TTL_SECONDS = max(300, settings.cache_ttl_seconds * 3)

INVALIDATE_USER_LUA = """
local catalog = redis.call('GET', KEYS[1]) or '1'
local current = redis.call('GET', KEYS[2]) or '0'
redis.call('DEL', 'loyalty:cashback:v' .. catalog .. ':u' .. ARGV[1] .. ':' .. current)
local next_version = redis.call('INCR', KEYS[2])
redis.call('EXPIRE', KEYS[2], ARGV[2])
return next_version
"""

RELEASE_LOCK_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


class TransactionIn(BaseModel):
    transaction_id: UUID = Field(default_factory=uuid4)
    user_id: int = Field(gt=0)
    category: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class RolloutIn(BaseModel):
    rollout_percent: int = Field(ge=0, le=100)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await create_pool(settings.database_url)
    await initialize(pool)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await redis.setnx(CATALOG_VERSION_KEY, 1)
    app.state.pool = pool
    app.state.redis = redis
    yield
    await redis.aclose()
    await pool.close()


app = FastAPI(
    title="Loyalty Cashback Service",
    version="1.0.0",
    description="Персональные cashback-офферы с Redis cache-aside",
    lifespan=lifespan,
)
app.mount("/metrics", make_asgi_app())


@app.middleware("http")
async def observe_http(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)
    started = time.perf_counter()
    IN_PROGRESS.inc()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        path = request.scope.get("route").path if request.scope.get("route") else request.url.path
        HTTP_REQUESTS.labels(request.method, path, str(status)).inc()
        HTTP_DURATION.labels(request.method, path).observe(time.perf_counter() - started)
        IN_PROGRESS.dec()


async def require_admin(x_admin_key: Annotated[str | None, Header()] = None) -> None:
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="invalid admin key")


async def cache_identity(redis: Redis, user_id: int) -> tuple[str, str]:
    user_version_key = f"loyalty:user-version:{user_id}"
    catalog_version, user_version = await redis.mget(
        CATALOG_VERSION_KEY, user_version_key
    )
    catalog_version = catalog_version or "1"
    user_version = user_version or "0"
    return (
        f"loyalty:cashback:v{catalog_version}:u{user_id}:{user_version}",
        user_version_key,
    )


async def calculate_from_db(request: Request, user_id: int) -> dict:
    started = time.perf_counter()
    try:
        async with request.app.state.pool.acquire() as conn:
            return await calculate_personalization(conn, user_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="user not found") from None
    finally:
        CALCULATION_TIME.observe(time.perf_counter() - started)


@app.get("/health")
async def health(request: Request):
    try:
        async with request.app.state.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        redis_ok = await request.app.state.redis.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok", "postgres": True, "redis": bool(redis_ok)}


@app.get("/api/v1/users/{user_id}/cashback")
async def get_cashback(user_id: int, request: Request):
    redis: Redis = request.app.state.redis
    try:
        cache_key, _ = await cache_identity(redis, user_id)
        cached = await redis.get(cache_key)
        if cached is not None:
            CACHE_REQUESTS.labels("hit").inc()
            result = json.loads(cached)
            result["cached"] = True
            return result
        CACHE_REQUESTS.labels("miss").inc()
    except Exception:
        CACHE_REQUESTS.labels("error").inc()
        result = await calculate_from_db(request, user_id)
        result["cached"] = False
        result["cache_degraded"] = True
        return result

    lock_key = f"{cache_key}:lock"
    lock_token = str(uuid4())
    try:
        acquired = await redis.set(lock_key, lock_token, nx=True, ex=5)
        if not acquired:
            for _ in range(8):
                await asyncio.sleep(0.025)
                cached = await redis.get(cache_key)
                if cached is not None:
                    CACHE_REQUESTS.labels("hit_after_wait").inc()
                    result = json.loads(cached)
                    result["cached"] = True
                    return result
    except Exception:
        CACHE_REQUESTS.labels("error").inc()
        result = await calculate_from_db(request, user_id)
        result["cached"] = False
        result["cache_degraded"] = True
        return result

    result = await calculate_from_db(request, user_id)
    ttl = settings.cache_ttl_seconds + random.randint(
        0, settings.cache_ttl_jitter_seconds
    )
    cache_degraded = False
    try:
        # Re-read versions: if a transaction raced with calculation, do not publish
        # the result under the new version.
        current_key, _ = await cache_identity(redis, user_id)
        if current_key == cache_key:
            await redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=ttl)
    except Exception:
        CACHE_REQUESTS.labels("error").inc()
        cache_degraded = True
    finally:
        if acquired:
            try:
                await redis.eval(RELEASE_LOCK_LUA, 1, lock_key, lock_token)
            except Exception:
                CACHE_REQUESTS.labels("error").inc()
    result["cached"] = False
    if cache_degraded:
        result["cache_degraded"] = True
    return result


@app.post("/api/v1/transactions")
async def register_transaction(payload: TransactionIn, request: Request):
    pool: asyncpg.Pool = request.app.state.pool
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Serializes transactions of one user and makes limit consumption atomic.
            await conn.execute("SELECT pg_advisory_xact_lock($1)", payload.user_id)
            previous = await conn.fetchrow(
                "SELECT * FROM transactions WHERE id = $1", payload.transaction_id
            )
            if previous:
                TRANSACTIONS.labels("idempotent_replay").inc()
                return {
                    "transaction_id": str(previous["id"]),
                    "user_id": previous["user_id"],
                    "offer_id": previous["offer_id"],
                    "cashback": float(previous["cashback"]),
                    "idempotent_replay": True,
                }

            try:
                personalized = await calculate_personalization(conn, payload.user_id)
            except KeyError:
                raise HTTPException(status_code=404, detail="user not found") from None

            candidates = [
                offer
                for offer in personalized["offers"]
                if offer["available"]
                and offer["category"] in (payload.category, "all")
            ]
            selected = max(
                candidates, key=lambda item: item["cashback_percent"], default=None
            )
            cashback = Decimal("0")
            offer_id = None
            if selected:
                offer_id = selected["offer_id"]
                calculated = payload.amount * Decimal(
                    str(selected["cashback_percent"])
                ) / Decimal("100")
                cashback = min(
                    calculated, Decimal(str(selected["remaining_limit"]))
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                await conn.execute(
                    """
                    INSERT INTO user_offer_usage (user_id, offer_id, cashback_used)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, offer_id) DO UPDATE
                    SET cashback_used = user_offer_usage.cashback_used + EXCLUDED.cashback_used
                    """,
                    payload.user_id,
                    offer_id,
                    cashback,
                )
            await conn.execute(
                "UPDATE users SET total_spent = total_spent + $2 WHERE id = $1",
                payload.user_id,
                payload.amount,
            )
            await conn.execute(
                """
                INSERT INTO transactions (id, user_id, offer_id, category, amount, cashback)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                payload.transaction_id,
                payload.user_id,
                offer_id,
                payload.category,
                payload.amount,
                cashback,
            )

    redis: Redis = request.app.state.redis
    try:
        user_version_key = f"loyalty:user-version:{payload.user_id}"
        await redis.eval(
            INVALIDATE_USER_LUA,
            2,
            CATALOG_VERSION_KEY,
            user_version_key,
            str(payload.user_id),
            str(USER_VERSION_TTL_SECONDS),
        )
    except Exception:
        # The bounded cache TTL remains the safety net if Redis is unavailable
        # immediately after the committed database transaction.
        CACHE_REQUESTS.labels("invalidation_error").inc()
    TRANSACTIONS.labels("created").inc()
    CASHBACK_AWARDED.labels(payload.category).inc(float(cashback))
    return {
        "transaction_id": str(payload.transaction_id),
        "user_id": payload.user_id,
        "offer_id": offer_id,
        "cashback": float(cashback),
        "idempotent_replay": False,
    }


@app.patch(
    "/api/v1/admin/offers/{offer_id}/rollout",
    dependencies=[Depends(require_admin)],
)
async def update_rollout(offer_id: int, payload: RolloutIn, request: Request):
    async with request.app.state.pool.acquire() as conn:
        updated = await conn.fetchrow(
            """
            UPDATE offers SET rollout_percent = $2 WHERE id = $1
            RETURNING id, name, rollout_percent
            """,
            offer_id,
            payload.rollout_percent,
        )
    if updated is None:
        raise HTTPException(status_code=404, detail="offer not found")
    try:
        catalog_version = await request.app.state.redis.incr(CATALOG_VERSION_KEY)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="offer changed in PostgreSQL, but cache version update failed; wait for TTL",
        ) from exc
    return {**dict(updated), "catalog_version": catalog_version}
