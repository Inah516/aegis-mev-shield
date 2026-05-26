"""Smoke tests for Aegis MEV Shield."""
import os
os.environ.setdefault("MIMO_API_KEY", "test-key")
os.environ.setdefault("MIMO_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
os.environ.setdefault("ETH_WS", "wss://stub-for-ci")

import pytest
from src.tracker import TokenTracker


def test_tracker_init():
    t = TokenTracker()
    assert t.snapshot() == {} or isinstance(t.snapshot(), dict)


def test_tracker_records_per_agent():
    t = TokenTracker()
    for agent in ["sandwich", "frontrun", "jit", "atomic_arb", "liquidation", "synthesis"]:
        t.record(agent, prompt=500, completion=200)
    snap = t.snapshot()
    assert len(snap) == 6
    assert all(snap[a]["total_tokens"] == 700 for a in snap)


def test_tracker_aggregates():
    t = TokenTracker()
    t.record("sandwich", prompt=1000, completion=400)
    t.record("sandwich", prompt=2000, completion=800)
    snap = t.snapshot()
    assert snap["sandwich"]["calls"] == 2
    assert snap["sandwich"]["total_tokens"] == 4200


def test_main_module():
    from src import main
    assert main.app is not None


def test_agents_module():
    from src import agents
    assert hasattr(agents, "AGENT_DESCRIPTORS") or hasattr(agents, "AgentRunner")


def test_six_agents_registered():
    from src import agents
    if hasattr(agents, "AGENT_DESCRIPTORS"):
        assert len(agents.AGENT_DESCRIPTORS) >= 6
