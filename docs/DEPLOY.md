# Aegis MEV Shield — Production Deploy

## Quick deploy (Docker)

```bash
docker build -t aegis-mev-shield .
docker run -d --name aegis \
  --restart unless-stopped \
  -p 8000:8000 \
  -e MIMO_API_KEY="$MIMO_API_KEY" \
  -e ETH_WS="$ETH_WS" \
  -e BASE_WS="$BASE_WS" \
  -e ARB_WS="$ARB_WS" \
  -e OP_WS="$OP_WS" \
  aegis-mev-shield
```

Health check:

```bash
curl -s http://localhost:8000/api/health | jq
```

WebSocket alert feed:

```bash
websocat ws://localhost:8000/api/feed
```

## systemd unit (Linux VPS)

`/etc/systemd/system/aegis.service`:

```ini
[Unit]
Description=Aegis MEV Shield
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=aegis
Group=aegis
WorkingDirectory=/opt/aegis
EnvironmentFile=/opt/aegis/.env
ExecStart=/opt/aegis/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Mempool subscription notes

- Use Alchemy / QuickNode / Blast premium for stable WSS
- Free public RPCs drop frames after 30s, will trigger reconnect storms
- Recommended: dedicated WSS per chain, not shared multi-chain endpoints
- Prefer `eth_subscribe` + `newPendingTransactions` over polling

## Token budget

Per-agent tracker exposed at `/api/stats`. Monitor consumption:

```bash
curl -s http://localhost:8000/api/stats | jq '.agents | to_entries | sort_by(-.value.total_tokens)'
```

Set hard cap on synthesis agent (most expensive) via env:

```env
MAX_SYNTHESIS_TOKENS_PER_HOUR=2000000
```
