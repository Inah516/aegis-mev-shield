"""Six MEV detection agents — fan-out + synthesis."""
import json
import logging
import os
import re
from dataclasses import dataclass

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("agents")


@dataclass
class AgentConfig:
    base_url: str
    api_key: str
    model: str

    @classmethod
    def from_env(cls):
        key = os.getenv("MIMO_API_KEY")
        if not key:
            raise RuntimeError("MIMO_API_KEY not set")
        return cls(
            base_url=os.getenv("MIMO_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1"),
            api_key=key,
            model=os.getenv("MIMO_MODEL", "mimo-v2.5-pro"),
        )


AGENT_DESCRIPTORS = [
    {
        "name": "sandwich_detector",
        "model": "mimo-v2.5-pro",
        "role": "Identify front+back transaction pairs wrapping a victim swap",
        "tokens_per_call": 12_000,
    },
    {
        "name": "frontrun_detector",
        "model": "mimo-v2.5-pro",
        "role": "Detect copycat transactions raising priority fee to land first",
        "tokens_per_call": 8_000,
    },
    {
        "name": "jit_liquidity_hunter",
        "model": "mimo-v2.5-pro",
        "role": "Identify just-in-time liquidity adds + removes around a single swap",
        "tokens_per_call": 14_000,
    },
    {
        "name": "atomic_arb_tracer",
        "model": "mimo-v2.5-pro",
        "role": "Trace cross-DEX arbitrage routes consuming pool imbalance",
        "tokens_per_call": 10_000,
    },
    {
        "name": "liquidation_spotter",
        "model": "mimo-v2.5-pro",
        "role": "Identify aave/compound/euler liquidation calls with bonus capture",
        "tokens_per_call": 9_000,
    },
    {
        "name": "synthesis_reasoner",
        "model": "mimo-v2.5-pro",
        "role": "Cross-correlate detector findings into a single risk score + attribution",
        "tokens_per_call": 16_000,
    },
]


class AgentRunner:
    def __init__(self, tracker, config: AgentConfig | None = None):
        self.config = config or AgentConfig.from_env()
        self.tracker = tracker
        self.client = AsyncOpenAI(base_url=self.config.base_url, api_key=self.config.api_key)

    async def aclose(self):
        await self.client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def _chat(self, agent: str, system: str, user: str, max_tokens: int = 4000) -> dict:
        resp = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        usage = resp.usage
        self.tracker.record(
            agent=agent,
            prompt=usage.prompt_tokens if usage else 0,
            completion=usage.completion_tokens if usage else 0,
        )
        choice = resp.choices[0]
        content = choice.message.content or ""
        reasoning = getattr(choice.message, "reasoning_content", None)
        return {"content": content, "reasoning": reasoning}

    @staticmethod
    def _parse_json(text: str) -> dict:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return {"parse_error": True, "raw": text[:500]}
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"parse_error": True, "raw": text[:500]}

    async def detect_sandwich(self, block_window: list[dict]) -> dict:
        system = (
            "You are a MEV sandwich attack detector. Given an ordered list of "
            "mempool/included transactions, identify any sandwich attack pattern: "
            "(attacker_front, victim, attacker_back) on the same pool same direction. "
            "Verify front/back are by same address, victim has insufficient slippage, "
            "and attacker captured price impact. Output JSON: "
            "{detected: bool, confidence: 0-100, attacker: addr, victim: addr, "
            "pool: addr, profit_usd: number, reasoning: short string}."
        )
        r = await self._chat(
            "sandwich_detector",
            system,
            json.dumps(block_window, separators=(",", ":"))[:30_000],
        )
        return self._parse_json(r["content"])

    async def detect_frontrun(self, block_window: list[dict]) -> dict:
        system = (
            "You are a MEV frontrun detector. Identify copycat transactions that "
            "duplicate another pending tx's call but with higher priority fee. "
            "Output JSON: {detected: bool, confidence: 0-100, frontrunner: addr, "
            "victim: addr, calldata_match: bool, fee_uplift_gwei: number}."
        )
        r = await self._chat(
            "frontrun_detector",
            system,
            json.dumps(block_window, separators=(",", ":"))[:30_000],
        )
        return self._parse_json(r["content"])

    async def detect_jit(self, block_window: list[dict]) -> dict:
        system = (
            "You are a Uniswap v3/v4 just-in-time liquidity detector. Identify "
            "(add_liquidity, swap, remove_liquidity) triples by the same address "
            "where the LP add is concentrated in the swap's price range and the "
            "remove happens within 1 block. Output JSON: {detected: bool, "
            "confidence: 0-100, lp_provider: addr, pool: addr, fee_captured_usd: number}."
        )
        r = await self._chat(
            "jit_liquidity_hunter",
            system,
            json.dumps(block_window, separators=(",", ":"))[:30_000],
        )
        return self._parse_json(r["content"])

    async def detect_atomic_arb(self, tx: dict) -> dict:
        system = (
            "You are an atomic-arbitrage tracer. Decode the tx call graph, identify "
            "cross-DEX legs (Uniswap, Curve, Balancer, Sushi, Maverick, etc), and "
            "compute the imbalance closure path. Output JSON: {detected: bool, "
            "confidence: 0-100, searcher: addr, route: [dex1, dex2, ...], "
            "profit_usd: number, dexes_consumed: int}."
        )
        r = await self._chat(
            "atomic_arb_tracer",
            system,
            json.dumps(tx, separators=(",", ":"))[:30_000],
        )
        return self._parse_json(r["content"])

    async def detect_liquidation(self, tx: dict) -> dict:
        system = (
            "You are a lending-protocol liquidation detector. Identify aave / compound / "
            "euler / morpho liquidationCall or similar functions, the bonus captured, "
            "and the borrower's collateral asset. Output JSON: {detected: bool, "
            "confidence: 0-100, liquidator: addr, borrower: addr, protocol: name, "
            "bonus_usd: number}."
        )
        r = await self._chat(
            "liquidation_spotter",
            system,
            json.dumps(tx, separators=(",", ":"))[:30_000],
        )
        return self._parse_json(r["content"])

    async def synthesize(self, findings: list[dict]) -> dict:
        system = (
            "You are the synthesis reasoner for an MEV detection pipeline. Given the "
            "findings from 5 specialized detectors against a block window, produce a "
            "unified attribution and risk assessment. Output JSON: "
            "{block_window_risk: 0-100, attack_categories: [string], top_attackers: "
            "[{addr, total_profit_usd, attack_count}], top_victims: [{addr, "
            "loss_usd, attack_type}], summary: short string}. "
            "Use chain-of-thought reasoning to attribute correctly."
        )
        r = await self._chat(
            "synthesis_reasoner",
            system,
            json.dumps(findings, separators=(",", ":"))[:30_000],
            max_tokens=2000,
        )
        out = self._parse_json(r["content"])
        out["reasoning_trace"] = r.get("reasoning")
        return out
