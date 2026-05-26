# Aegis MEV Shield

[![CI](https://github.com/Inah516/aegis-mev-shield/actions/workflows/ci.yml/badge.svg)](https://github.com/Inah516/aegis-mev-shield/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Powered by Xiaomi MiMo Pro](https://img.shields.io/badge/powered%20by-MiMo%20V2.5%20Pro-ff6700)](https://platform.xiaomimimo.com/)
[![Chains](https://img.shields.io/badge/chains-ETH%20%7C%20Base%20%7C%20Arb%20%7C%20OP-blueviolet)](#supported-chains)


> Continuous mempool surveillance and MEV attack classification across Ethereum, Base, Arbitrum, and Optimism. Six specialized AI agents fan out across pending transactions, classify sandwich / frontrun / JIT / atomic-arb / liquidation / generalized attacks, and surface attribution traces for the affected wallet.

[![MiMo](https://img.shields.io/badge/Powered%20by-Xiaomi%20MiMo%20V2.5-orange)](https://platform.xiaomimimo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## What it does

You give Aegis a wallet address (or a contract). Six agents run continuously against the mempool of every chain you monitor:

| Agent | Job | Tokens / call |
|---|---|---:|
| Sandwich Detector | Identify front + back transactions wrapping a victim swap | ~12K |
| Frontrun Detector | Detect copycat transactions raising priority fee to land first | ~8K |
| JIT Liquidity Hunter | Identify just-in-time liquidity adds + removes around a single swap | ~14K |
| Atomic-Arb Tracer | Trace cross-DEX arbitrage routes consuming pool imbalance | ~10K |
| Liquidation Spotter | Identify aave / compound / euler liquidation calls + bonus capture | ~9K |
| Synthesis Reasoner | Cross-correlate findings into a single risk score + attribution | ~16K |

Each agent runs `mimo-v2.5-pro`. Synthesis runs `mimo-v2.5-pro` with `reasoning_content` enabled to surface the chain-of-thought used for attribution.

## Architecture

```
                        Mempool Stream (websocket)
                             ETH / Base / Arb / Op
                                       │
                                       ▼
                        ┌────────────────────────────┐
                        │   Pre-filter (heuristic)    │
                        │   ─ Drop dust txs           │
                        │   ─ Group by block window   │
                        │   ─ Fan blocks to detectors │
                        └────────────────────────────┘
                                       │
              ┌──────────┬─────────────┼─────────────┬────────────┐
              │          │             │             │            │
        ┌─────▼─────┐ ┌──▼────┐ ┌──────▼────┐ ┌─────▼────┐ ┌─────▼────┐
        │ Sandwich  │ │ Front │ │    JIT    │ │ AtomicArb│ │ Liquid.  │
        │ Detector  │ │  Run  │ │ Liquidity │ │  Tracer  │ │ Spotter  │
        │           │ │ Detect│ │  Hunter   │ │          │ │          │
        └─────┬─────┘ └──┬────┘ └──────┬────┘ └─────┬────┘ └─────┬────┘
              │          │             │             │            │
              └──────────┴─────────────┼─────────────┴────────────┘
                                       │
                                       ▼
                        ┌────────────────────────────┐
                        │   Synthesis Reasoner        │
                        │   mimo-v2.5-pro             │
                        │   reasoning_content active  │
                        └────────────────────────────┘
                                       │
                                       ▼
                          Alert + Attribution Trace
```

## Token consumption profile

Continuous monitoring is naturally token-hungry. A single chain's mempool produces ~30 candidate blocks / minute that pass pre-filter. Each block fans out to all 6 detectors, then synthesis aggregates.

| Stage | Calls per block | Tokens per block |
|---|---:|---:|
| 5 detectors | 5 | ~53K |
| Synthesis | 1 | ~16K |
| **Per block** | **6** | **~69K** |

| Cadence | Tokens / hour | Tokens / day |
|---|---:|---:|
| Single chain at 30 blocks / min | ~124M | **~3B** |
| 4 chains parallel | ~496M | **~12B** |

This is before accounting for spikes during high-MEV events (Curve depeg, Uniswap v4 hook deploys, Blast LRT season). On those days the pre-filter relaxes and Aegis can hit **~20B tokens / day** organically.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Inah516/aegis-mev-shield.git
cd aegis-mev-shield

# 2. Install
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# edit .env:
#   MIMO_API_KEY=***
#   ETH_WS=wss://...
#   BASE_WS=wss://...
#   ARB_WS=wss://...
#   OP_WS=wss://...

# 4. Run
uvicorn src.main:app --reload --port 8000
```

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Provider + chain WS status |
| `/api/agents` | GET | List of 6 agents and their roles |
| `/api/scan/wallet/{address}` | GET | Full scan against historical mempool window |
| `/api/scan/contract/{address}` | GET | Risk profile for a contract being targeted |
| `/api/feed` | WebSocket | Real-time alert stream |
| `/api/stats` | GET | Per-agent token usage breakdown |

## Why MiMo V2.5

- **Long context** — full block + previous N blocks fits in one call for cross-block correlation
- **`reasoning_content`** — attribution trace is the most valuable output; reasoning visibility makes it auditable
- **Token Plan endpoint** — predictable cost on continuous workload
- **Pro tier reasoning** — sandwich attribution requires multi-step reasoning across mempool ordering + slot priority + slippage tolerance

## Detection details

### Sandwich detection

A sandwich attack consists of:
1. Front transaction by the attacker, raising priority fee, executing same-direction swap
2. Victim transaction with insufficient slippage protection
3. Back transaction by the attacker, reversing direction, capturing the price impact

The Sandwich Detector agent receives a 5-block window and must:
- Identify same-pool same-token-pair triplets ordered (attacker, victim, attacker)
- Verify the inner transaction has higher slippage than outer transactions
- Compute attacker P&L net of gas

It outputs a structured JSON record per detected sandwich plus a confidence score 0-100.

### JIT liquidity

Just-in-time liquidity is a Uniswap v3 / v4 specific pattern:
1. Attacker sees a large pending swap
2. Adds concentrated liquidity in the swap's price range
3. Captures the LP fee from the swap
4. Removes liquidity in the next block

JIT Hunter classifies the add+swap+remove triple and computes the LP fee captured.

### Atomic-arb tracer

Atomic arb spans multiple DEXes in one transaction. The tracer:
1. Decodes the transaction call graph
2. Identifies cross-DEX legs (Uniswap → Curve → Balancer → ...)
3. Computes the imbalance closure path and the searcher's profit

## Roadmap

- [x] 6 specialized agents fan-out
- [x] Per-agent token tracking with SQLite persistence
- [x] FastAPI backend + WebSocket alert stream
- [x] Synthesis with reasoning_content trace
- [ ] Solana mempool support (when Helius / Yellowstone Geyser stable)
- [ ] Streaming SSE responses
- [ ] Browser extension (paste a tx hash → instant classification)
- [ ] Public alert feed for dapps to subscribe

## Credits

Built for the [Xiaomi MiMo Open Source Incentive Program](https://platform.xiaomimimo.com/).

## License

MIT
