from fastapi import FastAPI
from pydantic import BaseModel
import os, asyncpg

app = FastAPI(title="tripstats")
DB_URL = os.environ["DATABASE_URL"]  # injected by env, never hardcoded
_pool = None


class Trip(BaseModel):
    city: str
    distance_km: float


async def pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DB_URL)
        async with _pool.acquire() as c:
            await c.execute("""CREATE TABLE IF NOT EXISTS trips(
                id SERIAL PRIMARY KEY, city TEXT, distance_km DOUBLE PRECISION)""")
    return _pool


@app.get("/healthz")  # liveness/readiness target — keep it cheap
async def healthz():
    return {"status": "ok"}


@app.post("/trips")
async def add_trip(t: Trip):
    p = await pool()
    async with p.acquire() as c:
        await c.execute("INSERT INTO trips(city, distance_km) VALUES($1,$2)",
                        t.city, t.distance_km)
    return {"inserted": True}


@app.get("/stats/{city}")
async def stats(city: str):
    p = await pool()
    async with p.acquire() as c:
        row = await c.fetchrow(
            "SELECT count(*) n, coalesce(avg(distance_km),0) avg_km FROM trips WHERE city=$1",
            city)
    return {"city": city, "trips": row["n"], "avg_km": round(row["avg_km"], 2)}
