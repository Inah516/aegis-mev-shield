"""Aegis Engine — orchestrates chains + agents."""
import asyncio
import logging
import os
import time
from dataclasses import dataclass

from src.agents import AgentRunner, AGENT_DESCRIPTORS, AgentConfig
from src.tracker import TokenTracker

logger = logging.getLogger("engine")


@dataclass
class EngineConfig:
    model: str
    chains: dict[str, str]  # name -> ws_url
    min_victim_usd: float
    sandwich_profit_floor: float
    jit_fee_floor: float

    @classmethod
    def from_env(cls):
        chains = {
            name: os.getenv(f"{name.upper()}_WS", "")
            for name in ("eth", "base", "arb", "op")
        }
        return cls(
            model=os.getenv("MIMO_MODEL", "mimo-v2.5-pro"),
            chains={k: v for k, v in chains.items() if v},
            min_victim_usd=float(os.getenv("MIN_VICTIM_USD", "500")),
            sandwich_profit_floor=float(os.getenv("SANDWICH_PROFIT_FLOOR_USD", "20")),
            jit_fee_floor=float(os.getenv("JIT_FEE_FLOOR_USD", "10")),
        )


class Engine:
    def __init__(self, tracker: TokenTracker):
        self.config = EngineConfig.from_env()
        self.tracker = tracker
        self.agent = AgentRunner(tracker=tracker, config=AgentConfig.from_env())
        self.chains = self.config.chains
        self._subscribers: list[asyncio.Queue] = []
        self._tasks: list[asyncio.Task] = []
        self._started = time.time()

    async def start(self):
        # Listener stub — real implementation would use eth-account websocket subscriptions
        # and feed blocks to the agent runner. Stubbed here so the API surface is testable.
        logger.info("Engine start (chains=%d)", len(self.chains))

    async def stop(self):
        for t in self._tasks:
            t.cancel()
        await self.agent.aclose()

    def chain_status(self) -> dict:
        return {name: {"ws": bool(url)} for name, url in self.chains.items()}

    def uptime_seconds(self) -> int:
        return int(time.time() - self._started)

    def agent_descriptors(self) -> list:
        return AGENT_DESCRIPTORS

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def _broadcast(self, alert: dict):
        for q in list(self._subscribers):
            try:
                q.put_nowait(alert)
            except asyncio.QueueFull:
                logger.warning("subscriber queue full, dropping alert")

    async def scan_wallet(self, address: str, blocks: int = 50) -> dict:
        """Run all agents against a synthetic block window for a wallet."""
        # Stub block window — production code would fetch the real mempool history
        # for the address from a node provider.
        block_window = [
            {"hash": f"0x{i:064x}", "from": address, "to": "0x", "value_usd": 0}
            for i in range(blocks)
        ]
        results = await asyncio.gather(
            self.agent.detect_sandwich(block_window),
            self.agent.detect_frontrun(block_window),
            self.agent.detect_jit(block_window),
            return_exceptions=True,
        )
        findings = []
        for r in results:
            if isinstance(r, Exception):
                findings.append({"error": str(r)})
            else:
                findings.append(r)
        synthesis = await self.agent.synthesize(findings)
        return {
            "wallet": address,
            "blocks_scanned": blocks,
            "findings": findings,
            "synthesis": synthesis,
        }

    async def scan_contract(self, address: str, blocks: int = 50) -> dict:
        """Run liquidation + atomic-arb detectors against a contract's recent activity."""
        tx_stub = {"to": address, "blocks": blocks}
        results = await asyncio.gather(
            self.agent.detect_liquidation(tx_stub),
            self.agent.detect_atomic_arb(tx_stub),
            return_exceptions=True,
        )
        findings = [r if not isinstance(r, Exception) else {"error": str(r)} for r in results]
        synthesis = await self.agent.synthesize(findings)
        return {
            "contract": address,
            "blocks_scanned": blocks,
            "findings": findings,
            "synthesis": synthesis,
        }
