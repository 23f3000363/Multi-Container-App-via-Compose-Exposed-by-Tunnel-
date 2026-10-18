
import os
import time

import redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

r = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def wait_for_redis():
    for attempt in range(30):
        try:
            r.ping()
            print("Redis connection successful")
            return
        except redis.RedisError as exc:
            print(f"Waiting for Redis ({attempt + 1}/30): {exc}")
            time.sleep(1)

    raise RuntimeError("Could not connect to Redis")


@app.post("/hit/{key}")
def hit(key: str):
    try:
        count = r.incr(f"hits:{key}")
        return {"key": key, "count": count}
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")


@app.get("/count/{key}")
def count(key: str):
    try:
        value = r.get(f"hits:{key}")
        return {"key": key, "count": int(value) if value is not None else 0}
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")


@app.get("/healthz")
def healthz():
    try:
        r.ping()
        return {"status": "ok", "redis": "up"}
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")
