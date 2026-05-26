"""Aegis MEV Shield — FastAPI gateway."""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from src.engine import Engine
from src.tracker import TokenTracker

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("aegis")

engine: Engine | None = None
tracker = TokenTracker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = Engine(tracker=tracker)
    await engine.start()
    logger.info("Aegis ready (model=%s, chains=%d)", engine.config.model, len(engine.chains))
    yield
    await engine.stop()


app = FastAPI(
    title="Aegis MEV Shield",
    description="Multi-chain mempool surveillance and MEV attack classification",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "provider": "xiaomi-mimo",
        "model": engine.config.model,
        "chains": engine.chain_status(),
        "uptime_seconds": engine.uptime_seconds(),
    }


@app.get("/api/agents")
async def agents():
    return {"agents": engine.agent_descriptors()}


@app.get("/api/stats")
async def stats():
    return tracker.snapshot()


@app.get("/api/scan/wallet/{address}")
async def scan_wallet(address: str, blocks: int = 50):
    try:
        return await engine.scan_wallet(address, blocks=blocks)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/scan/contract/{address}")
async def scan_contract(address: str, blocks: int = 50):
    try:
        return await engine.scan_contract(address, blocks=blocks)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.websocket("/api/feed")
async def feed(ws: WebSocket):
    await ws.accept()
    queue = engine.subscribe()
    try:
        while True:
            alert = await queue.get()
            await ws.send_json(alert)
    except WebSocketDisconnect:
        engine.unsubscribe(queue)
