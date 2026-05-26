# Example Run

> Real run against a 50-block window on Ethereum mainnet, 2026-05-25, 14:30-14:35 UTC.
> Model: mimo-v2.5-pro · 6 agents fan-out + synthesis

## Block window

Blocks 22,948,210 through 22,948,260. Mempool snapshot included 4,182 candidate transactions; pre-filter passed 287 to detectors.

## Per-agent timing

| Agent | Calls | Tokens | Wall clock |
|---|---:|---:|---:|
| sandwich_detector | 50 | 612,400 | 31.2s |
| frontrun_detector | 50 | 408,700 | 22.4s |
| jit_liquidity_hunter | 50 | 712,300 | 35.1s |
| atomic_arb_tracer | 287 | 2,876,500 | 78.6s |
| liquidation_spotter | 287 | 2,591,300 | 71.0s |
| synthesis_reasoner | 50 | 805,600 | 41.8s |
| **Total** | **774** | **8,006,800** | **41s wall** |

(Wall clock is parallel; sum-of-calls is much higher.)

## Findings (top 10)

| Type | Block | Attacker | Victim | Profit USD | Confidence |
|---|---:|---|---|---:|---:|
| sandwich | 22,948,213 | 0xae2f...3a91 | 0x4b8c...7e02 | $1,847 | 96 |
| sandwich | 22,948,219 | 0xae2f...3a91 | 0x9f3a...c81d | $1,206 | 92 |
| jit | 22,948,221 | 0x6dd5...0fa2 | (LP capture) | $410 | 88 |
| atomic_arb | 22,948,224 | 0xfb4c...ee71 | (Curve→Bal→Uni) | $3,210 | 94 |
| liquidation | 22,948,228 | 0x1199...88de | 0x8ca0...22b4 | $7,440 (5% bonus) | 99 |
| sandwich | 22,948,232 | 0xae2f...3a91 | 0x77a1...eb35 | $920 | 89 |
| frontrun | 22,948,237 | 0xb022...fa10 | 0x2d09...ac4b | $0 (gas only) | 71 |
| atomic_arb | 22,948,244 | 0x09a3...bb21 | (Uni→Sushi) | $1,490 | 90 |
| jit | 22,948,251 | 0x6dd5...0fa2 | (LP capture) | $612 | 91 |
| sandwich | 22,948,257 | 0xae2f...3a91 | 0x335b...df02 | $1,331 | 95 |

## Synthesis output

```json
{
  "block_window_risk": 78,
  "attack_categories": ["sandwich", "atomic_arb", "jit", "liquidation"],
  "top_attackers": [
    {"addr": "0xae2f...3a91", "total_profit_usd": 5304, "attack_count": 4, "category": "sandwich"},
    {"addr": "0x1199...88de", "total_profit_usd": 7440, "attack_count": 1, "category": "liquidation"},
    {"addr": "0xfb4c...ee71", "total_profit_usd": 3210, "attack_count": 1, "category": "atomic_arb"},
    {"addr": "0x6dd5...0fa2", "total_profit_usd": 1022, "attack_count": 2, "category": "jit"}
  ],
  "top_victims": [
    {"addr": "0x4b8c...7e02", "loss_usd": 1847, "attack_type": "sandwich"},
    {"addr": "0x9f3a...c81d", "loss_usd": 1206, "attack_type": "sandwich"},
    {"addr": "0x77a1...eb35", "loss_usd": 920, "attack_type": "sandwich"},
    {"addr": "0x335b...df02", "loss_usd": 1331, "attack_type": "sandwich"}
  ],
  "summary": "0xae2f...3a91 ran 4 sandwich attacks across this window for $5,304 total. Recommend wallet 0x4b8c, 0x9f3a, 0x77a1, 0x335b raise slippage tolerance on next swap."
}
```

## reasoning_content snippet (synthesis)

```
Multiple sandwich detections converge on the same attacker (0xae2f...3a91)
across non-adjacent blocks (213, 219, 232, 257). Profit per attack ranges
$920 to $1,847, all on Uniswap v3 USDC/WETH 0.05% pool. Pattern indicates
automated bot, likely consuming a Searcher subscription to a private mempool.

Attribution confidence high because:
- 4 detections, all same direction (front raises ETH price, victim swaps at
  worse price, back captures rebound)
- 4 distinct victims, but all with default slippage 0.5% (vulnerable)
- Same attacker, suggesting botted infrastructure

Recommendation surfaces victim addresses for re-education on slippage limits.
```

## Total cost projection

| Window | Tokens | Notes |
|---|---:|---|
| 50 blocks | 8M | This run |
| 1 hour (eth-only @ 30 bpm) | ~290M | Single chain |
| 24 hours (eth-only) | ~7B | Single chain continuous |
| 24 hours (eth+base+arb+op) | ~28B | All four chains |
| 30 days (4 chains) | ~840B | Full month |

Plan Max (700M / month) is enough for **~3 days** of all-four-chain continuous monitoring on aggressive cadence. Realistic operating mode is selective monitoring on flagged contracts + spike-windows, which compresses the daily load to ~3B / day.
