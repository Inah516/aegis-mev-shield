"""Token usage tracker — per-agent breakdown."""
import time
from collections import defaultdict
from threading import Lock


class TokenTracker:
    def __init__(self):
        self._lock = Lock()
        self._stats: dict[str, dict] = defaultdict(lambda: {
            "prompt": 0, "completion": 0, "calls": 0, "errors": 0,
        })
        self._started = time.time()

    def record(self, agent: str, prompt: int, completion: int):
        with self._lock:
            s = self._stats[agent]
            s["prompt"] += prompt
            s["completion"] += completion
            s["calls"] += 1

    def record_error(self, agent: str):
        with self._lock:
            self._stats[agent]["errors"] += 1

    def snapshot(self) -> dict:
        with self._lock:
            agents = {
                a: {
                    "prompt_tokens": s["prompt"],
                    "completion_tokens": s["completion"],
                    "total_tokens": s["prompt"] + s["completion"],
                    "calls": s["calls"],
                    "errors": s["errors"],
                } for a, s in self._stats.items()
            }
            return {
                "uptime_seconds": int(time.time() - self._started),
                "agents": agents,
                "total_tokens": sum(a["total_tokens"] for a in agents.values()),
                "total_calls": sum(a["calls"] for a in agents.values()),
            }
