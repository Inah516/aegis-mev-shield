#!/usr/bin/env python3
"""Example client for Aegis MEV Shield.

Usage:
    python examples/client.py scan-wallet 0x1234...
    python examples/client.py scan-block 22948210 --chain ethereum
    python examples/client.py stats
"""
from __future__ import annotations

import argparse
import json
import sys

import httpx

DEFAULT_BASE = "http://localhost:8000"


def main() -> int:
    parser = argparse.ArgumentParser(description="Aegis MEV Shield client")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sw = sub.add_parser("scan-wallet")
    sw.add_argument("address")
    sw.add_argument("--chain", default="ethereum")

    sb = sub.add_parser("scan-block")
    sb.add_argument("block", type=int)
    sb.add_argument("--chain", default="ethereum")

    sub.add_parser("stats")

    parser.add_argument("--base", default=DEFAULT_BASE)
    args = parser.parse_args()

    if args.cmd == "scan-wallet":
        r = httpx.get(f"{args.base}/api/scan/wallet/{args.address}",
                      params={"chain": args.chain}, timeout=120)
    elif args.cmd == "scan-block":
        r = httpx.get(f"{args.base}/api/scan/block/{args.block}",
                      params={"chain": args.chain}, timeout=120)
    elif args.cmd == "stats":
        r = httpx.get(f"{args.base}/api/stats", timeout=10)
    else:
        parser.print_help()
        return 2

    r.raise_for_status()
    print(json.dumps(r.json(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
