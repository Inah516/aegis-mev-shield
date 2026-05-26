# Architecture

Aegis is a multi-agent, multi-chain MEV detection system. Six specialized LLM agents run on `mimo-v2.5-pro` and process the mempool stream of every supported chain.

## Pipeline

```
WebSocket subscription per chain
  │
  ▼
Block window builder (5-block sliding window)
  │
  ├── Pre-filter (heuristic, no LLM call)
  │     ─ Drop dust txs (value < $500)
  │     ─ Drop empty / failed receipts
  │     ─ Group by block + sub-window
  │
  ▼
Per-block fan-out (parallel)
  │
  ├── SandwichDetector       → (front, victim, back) triplets
  ├── FrontrunDetector       → priority-fee uplift on copycat calldata
  ├── JITLiquidityHunter     → (add, swap, remove) LP triples in 1-block range
  ├── AtomicArbTracer        → cross-DEX route reconstruction
  └── LiquidationSpotter     → aave/compound/euler liquidationCall
  │
  ▼
SynthesisReasoner
  │  ─ Cross-correlate findings into one risk score
  │  ─ Attribute to top attacker / top victim
  │  ─ Surface reasoning_content for audit trail
  │
  ▼
Alert broadcast
  │
  ├── WebSocket /api/feed subscribers
  └── Postgres alert log (optional)
```

## Why fan-out

Each detector is a domain specialist. Running them in parallel on the same block window exposes the data to multiple complementary lenses simultaneously. The same swap might be classified as both sandwich-victim and JIT-victim — the synthesis step reconciles overlapping classifications.

## Why MiMo V2.5 Pro

| Feature | Value for this workload |
|---|---|
| Long context window | Full block + N previous blocks fits in one call for cross-block correlation |
| `reasoning_content` | Attribution trace is the most valuable output; reasoning visibility makes it auditable |
| Token Plan endpoint | Predictable cost on continuous workload |
| Pro tier reasoning | Sandwich attribution requires multi-step reasoning across mempool ordering, slot priority, slippage tolerance |

## Token consumption

Continuous monitoring is naturally token-hungry. Per block window:

| Stage | Calls | Tokens |
|---|---:|---:|
| 5 detectors | 5 | ~53K |
| Synthesis | 1 | ~16K |
| **Per block** | **6** | **~69K** |

| Cadence | Tokens / hour | Tokens / day |
|---|---:|---:|
| Single chain @ 30 blocks/min | ~124M | **~3B** |
| 4 chains parallel | ~496M | **~12B** |
| Spike events (Curve depeg, hook deploys, LRT season) | ~830M | **~20B** |

This is organic load, not synthetic. Every block on every chain triggers the same 6-call fan-out.

## Detection details

### Sandwich

A sandwich attack requires:
1. Front transaction by attacker (raises priority fee, swap direction A → B)
2. Victim transaction with insufficient slippage (same pool, same direction A → B)
3. Back transaction by attacker (swap direction B → A, capturing price impact)

The detector receives a 5-block window and must:
- Identify same-pool same-pair triplets ordered (attacker, victim, attacker)
- Verify inner tx has higher slippage tolerance than outer txs
- Compute attacker P&L net of gas

Output is a structured JSON record per detected sandwich plus confidence 0-100.

### JIT liquidity

Just-in-time liquidity is Uniswap v3 / v4 specific:
1. Attacker sees a large pending swap
2. Adds concentrated liquidity in the swap's price range
3. Captures the LP fee
4. Removes liquidity in the next block

The hunter classifies the (add, swap, remove) triple and computes the LP fee captured.

### Atomic arb

Atomic arbitrage spans multiple DEXes in a single transaction. The tracer:
1. Decodes the transaction's call graph
2. Identifies cross-DEX legs (Uniswap → Curve → Balancer → Sushi → ...)
3. Computes the imbalance closure path and the searcher's profit

Tokens per call are higher (~10K) because the call graph itself is large.

## Failure modes

| Failure | Mitigation |
|---|---|
| Single agent timeout | Tenacity retry with exponential backoff (3 attempts) |
| Malformed JSON output | Regex match + fallback to raw text |
| Chain WS reconnect | Auto-reconnect on disconnect, replay last 50 blocks on resume |
| One detector failing | Pipeline catches per-agent exception; synthesis runs with partial findings |
| Pre-filter false negative | Sliding window catches missed patterns within 5 blocks |

## Storage

SQLite (`./data/aegis.db`) records:
- Per-call token usage (agent, model, prompt, completion, duration)
- Detection records (chain, block, type, attacker, victim, profit, confidence)
- Alert log (timestamp, alert payload, subscriber count)

Stats endpoint queries this for real-time and historical breakdowns.

## Provider portability

All LLM calls go through `AsyncOpenAI` configured via `MIMO_BASE_URL` and `MIMO_API_KEY`. Swap providers via `.env`:

```env
# Xiaomi MiMo Token Plan (default — recommended for the reasoning workload)
MIMO_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5-pro

# OpenAI fallback
MIMO_BASE_URL=https://api.openai.com/v1
MIMO_MODEL=gpt-4o
```
