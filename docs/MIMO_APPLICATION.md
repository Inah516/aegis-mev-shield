# Xiaomi MiMo Open Source Incentive — Application Draft

> Submission target: <https://platform.xiaomimimo.com/>
> Project: **Aegis MEV Shield**
> GitHub: <https://github.com/Inah516/aegis-mev-shield>

---

## Project name
**Aegis MEV Shield** — multi-chain mempool surveillance and MEV attack classification powered by Xiaomi MiMo V2.5 Pro

## Project URL / Repo
`https://github.com/Inah516/aegis-mev-shield`

## Applicant role
DeFi infrastructure developer building real-time MEV detection tooling. Active across Ethereum, Base, Arbitrum, and Optimism mempools.

## AI tools currently used
- **OpenClaw** for orchestration
- **Cursor + Claude Code** for code editing
- **Foundry / Forge** for contract simulation

## Underlying models used today
GPT-5 class for reasoning. Claude Sonnet 4.x for long-context attribution. Looking to add **Xiaomi MiMo V2.5 Pro** as the primary model for the mempool detection workload because of its `reasoning_content` field and Token Plan endpoint pricing.

## Project description

### Problem
MEV is the largest single source of value extraction from DeFi users — sandwich attacks, JIT liquidity, and frontrunning collectively bleed hundreds of millions per year from passive swappers. Existing detection tools are either:
- **Reactive** (post-hoc analytics on Dune / Flashbots data, useful for research but not protection)
- **Bot-only** (private mempool subscriptions like blocknative, expensive, not user-facing)
- **Single-pattern** (sandwich-only, miss JIT and atomic-arb)

Aegis is multi-pattern, real-time, and attribution-focused. It tells the affected wallet *who* attacked them, *how much* was lost, and *what to change* on the next swap.

### Solution: Aegis MEV Shield

A FastAPI gateway with six MiMo-V2.5-Pro agents fanning out across the mempool of every supported chain:

1. **Sandwich Detector** — front + back triplet identification with slippage verification
2. **Frontrun Detector** — copycat calldata with priority-fee uplift
3. **JIT Liquidity Hunter** — Uniswap v3/v4 add+swap+remove triple within 1 block
4. **Atomic-Arb Tracer** — cross-DEX route reconstruction
5. **Liquidation Spotter** — aave/compound/euler liquidationCall + bonus capture
6. **Synthesis Reasoner** — cross-correlate findings, surface attribution with `reasoning_content` trace

### Why MiMo V2.5 Pro specifically

- **Long context** — full block + previous N blocks fits in one call for cross-block sandwich correlation
- **`reasoning_content`** — attribution audit trail visible to the operator and the affected wallet
- **Pro-tier reasoning** — sandwich attribution requires multi-step reasoning across ordering + slot priority + slippage
- **Token Plan endpoint** — predictable cost on continuous workload
- **OpenAI-compatible** — drop-in via `MIMO_BASE_URL` + `MIMO_API_KEY`

### Token consumption profile

Per block window (5 blocks):

| Stage | Calls | Tokens |
|---|---:|---:|
| 5 detectors | 5 | ~53K |
| Synthesis | 1 | ~16K |
| **Per block** | **6** | **~69K** |

Operating cadences:
- Single chain at 30 blocks / min = **~3B tokens / day**
- 4 chains parallel = **~12B tokens / day**
- Spike events (Curve depeg, hook deploys, LRT season) = **~20B tokens / day**

Realistic average: **6-9B tokens / day** sustained, **~200B / month**.

### Real run reference

Run against a 50-block Ethereum window (2026-05-25, 14:30-14:35 UTC):
- 287 candidate txs passed pre-filter
- 8M tokens consumed (parallel across 6 agents, 41s wall clock)
- 10 attacks identified, attribution complete
- Top attacker `0xae2f...3a91` ran 4 sandwich attacks for $5,304 total
- Synthesis surfaced victim addresses with slippage recommendations

Full breakdown in `docs/EXAMPLE_RUN.md`.

### What credits will be used for

- **Phase 1 (week 1-2)**: Production rollout on Ethereum mainnet, telemetry baseline
- **Phase 2 (week 3-4)**: Add Base + Arbitrum + Optimism mempool subscriptions
- **Phase 3 (month 2)**: Public WebSocket alert feed for dapps to subscribe (Uniswap, 1inch, Cowswap)
- **Phase 4 (month 3+)**: Solana mempool support (Yellowstone Geyser when stable)

Daily target during scale-out: **6-9B tokens / day** — comfortable Plan Max territory.

## Proof / artifacts

- **Repo (public)**: <https://github.com/Inah516/aegis-mev-shield>
- **Working FastAPI backend**: 6 endpoints (`/api/health`, `/api/agents`, `/api/scan/wallet/{addr}`, `/api/scan/contract/{addr}`, `/api/feed` WebSocket, `/api/stats`)
- **Real run artifact** in `docs/EXAMPLE_RUN.md` — 8M tokens, 50-block Ethereum window, 10 attacks classified
- **Architecture doc** in `docs/ARCHITECTURE.md`
- **Dockerfile** for prod deploy
- **Per-agent token tracking** with SQLite persistence

## Estimated tier requested

- **Plan Max** — 700M tokens / month is the right starting tier for selective-monitoring mode (~3B / day with smart pre-filter throttling)
- During scale-out to all 4 chains, request balance grant top-up to support spike events
- Whichever fits the evaluation outcome

## Email for application
*(use the email on `platform.xiaomimimo.com` account)*

## Notes for filling form

- Be specific about **MiMo Pro tier** — the reasoning workload genuinely needs Pro, not Instruct
- Mention the **`reasoning_content` field** — attribution audit trail is the unique value prop
- Real production run with concrete attribution (not synthetic load) > demo project
- Form note says: "the more detailed and specific, the higher the approval rate and tier."

## Submission checklist
- [x] Push repo to GitHub (public)
- [ ] Verify email matches `platform.xiaomimimo.com` account
- [ ] Click "立即申请" on landing page
- [ ] Paste fields above into the form
- [ ] Wait ~3 business days for evaluation email
- [ ] Once approved: connect production mempool feeds

## Post-approval roadmap
- Week 1: Ethereum-only baseline, telemetry verified
- Week 2: Add Base + Arb + Op
- Week 3: Public alert feed prototype
- Week 4: Browser extension (paste tx hash → instant classification)
- Month 2+: Solana mempool support
