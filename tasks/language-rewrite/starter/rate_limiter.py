"""
Rate Limiter Service

A configurable rate limiting service supporting multiple algorithms:
- Sliding Window: Counts requests in a rolling time window
- Token Bucket: Refills tokens at a steady rate, allows bursts

HTTP API for checking and consuming rate limits by client key.
"""

import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


class Algorithm(Enum):
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimitConfig:
    algorithm: Algorithm
    max_requests: int
    window_seconds: float
    burst_size: Optional[int] = None

    def __post_init__(self):
        if self.algorithm == Algorithm.TOKEN_BUCKET and self.burst_size is None:
            self.burst_size = self.max_requests


@dataclass
class SlidingWindowState:
    timestamps: list = field(default_factory=list)

    def cleanup(self, window_start: float) -> None:
        self.timestamps = [ts for ts in self.timestamps if ts >= window_start]

    def count(self) -> int:
        return len(self.timestamps)

    def add(self, timestamp: float) -> None:
        self.timestamps.append(timestamp)


@dataclass
class TokenBucketState:
    tokens: float
    last_refill: float

    def refill(self, now: float, refill_rate: float, max_tokens: int) -> None:
        elapsed = now - self.last_refill
        self.tokens = min(max_tokens, self.tokens + elapsed * refill_rate)
        self.last_refill = now

    def consume(self, count: int = 1) -> bool:
        if self.tokens >= count:
            self.tokens -= count
            return True
        return False


class RateLimiter:
    def __init__(self):
        self.configs: dict[str, RateLimitConfig] = {}
        self.sliding_window_states: dict[str, dict[str, SlidingWindowState]] = {}
        self.token_bucket_states: dict[str, dict[str, TokenBucketState]] = {}
        self.lock = threading.Lock()

    def configure(self, name: str, config: RateLimitConfig) -> None:
        with self.lock:
            self.configs[name] = config
            self.sliding_window_states[name] = {}
            self.token_bucket_states[name] = {}

    def remove_config(self, name: str) -> bool:
        with self.lock:
            if name not in self.configs:
                return False
            del self.configs[name]
            self.sliding_window_states.pop(name, None)
            self.token_bucket_states.pop(name, None)
            return True

    def get_config(self, name: str) -> Optional[RateLimitConfig]:
        with self.lock:
            return self.configs.get(name)

    def list_configs(self) -> list[str]:
        with self.lock:
            return list(self.configs.keys())

    def check(self, name: str, key: str, cost: int = 1) -> dict:
        with self.lock:
            config = self.configs.get(name)
            if not config:
                return {"error": "config_not_found", "allowed": False}

            now = time.time()

            if config.algorithm == Algorithm.SLIDING_WINDOW:
                return self._check_sliding_window(name, key, config, now, cost)
            else:
                return self._check_token_bucket(name, key, config, now, cost)

    def _check_sliding_window(
        self, name: str, key: str, config: RateLimitConfig, now: float, cost: int
    ) -> dict:
        states = self.sliding_window_states[name]
        if key not in states:
            states[key] = SlidingWindowState()

        state = states[key]
        window_start = now - config.window_seconds
        state.cleanup(window_start)

        current_count = state.count()
        remaining = max(0, config.max_requests - current_count)
        reset_at = now + config.window_seconds

        return {
            "allowed": current_count + cost <= config.max_requests,
            "remaining": remaining,
            "limit": config.max_requests,
            "reset_at": reset_at,
            "algorithm": "sliding_window",
        }

    def _check_token_bucket(
        self, name: str, key: str, config: RateLimitConfig, now: float, cost: int
    ) -> dict:
        states = self.token_bucket_states[name]
        if key not in states:
            states[key] = TokenBucketState(
                tokens=float(config.burst_size), last_refill=now
            )

        state = states[key]
        refill_rate = config.max_requests / config.window_seconds
        state.refill(now, refill_rate, config.burst_size)

        seconds_until_token = (cost - state.tokens) / refill_rate if state.tokens < cost else 0
        reset_at = now + max(0, seconds_until_token)

        return {
            "allowed": state.tokens >= cost,
            "remaining": int(state.tokens),
            "limit": config.burst_size,
            "reset_at": reset_at,
            "algorithm": "token_bucket",
        }

    def consume(self, name: str, key: str, cost: int = 1) -> dict:
        with self.lock:
            config = self.configs.get(name)
            if not config:
                return {"error": "config_not_found", "allowed": False}

            now = time.time()

            if config.algorithm == Algorithm.SLIDING_WINDOW:
                return self._consume_sliding_window(name, key, config, now, cost)
            else:
                return self._consume_token_bucket(name, key, config, now, cost)

    def _consume_sliding_window(
        self, name: str, key: str, config: RateLimitConfig, now: float, cost: int
    ) -> dict:
        states = self.sliding_window_states[name]
        if key not in states:
            states[key] = SlidingWindowState()

        state = states[key]
        window_start = now - config.window_seconds
        state.cleanup(window_start)

        current_count = state.count()

        if current_count + cost > config.max_requests:
            return {
                "allowed": False,
                "remaining": 0,
                "limit": config.max_requests,
                "reset_at": now + config.window_seconds,
                "algorithm": "sliding_window",
            }

        for _ in range(cost):
            state.add(now)

        remaining = config.max_requests - state.count()
        return {
            "allowed": True,
            "remaining": remaining,
            "limit": config.max_requests,
            "reset_at": now + config.window_seconds,
            "algorithm": "sliding_window",
        }

    def _consume_token_bucket(
        self, name: str, key: str, config: RateLimitConfig, now: float, cost: int
    ) -> dict:
        states = self.token_bucket_states[name]
        if key not in states:
            states[key] = TokenBucketState(
                tokens=float(config.burst_size), last_refill=now
            )

        state = states[key]
        refill_rate = config.max_requests / config.window_seconds
        state.refill(now, refill_rate, config.burst_size)

        allowed = state.consume(cost)

        seconds_until_token = (1 - state.tokens) / refill_rate if state.tokens < 1 else 0
        reset_at = now + max(0, seconds_until_token)

        return {
            "allowed": allowed,
            "remaining": int(state.tokens),
            "limit": config.burst_size,
            "reset_at": reset_at,
            "algorithm": "token_bucket",
        }

    def reset(self, name: str, key: str) -> bool:
        with self.lock:
            if name not in self.configs:
                return False

            config = self.configs[name]
            if config.algorithm == Algorithm.SLIDING_WINDOW:
                if key in self.sliding_window_states.get(name, {}):
                    del self.sliding_window_states[name][key]
            else:
                if key in self.token_bucket_states.get(name, {}):
                    del self.token_bucket_states[name][key]
            return True

    def stats(self, name: str) -> Optional[dict]:
        with self.lock:
            config = self.configs.get(name)
            if not config:
                return None

            if config.algorithm == Algorithm.SLIDING_WINDOW:
                states = self.sliding_window_states.get(name, {})
                return {
                    "name": name,
                    "algorithm": "sliding_window",
                    "active_keys": len(states),
                    "config": {
                        "max_requests": config.max_requests,
                        "window_seconds": config.window_seconds,
                    },
                }
            else:
                states = self.token_bucket_states.get(name, {})
                return {
                    "name": name,
                    "algorithm": "token_bucket",
                    "active_keys": len(states),
                    "config": {
                        "max_requests": config.max_requests,
                        "window_seconds": config.window_seconds,
                        "burst_size": config.burst_size,
                    },
                }


limiter = RateLimiter()


class RateLimiterHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> Optional[dict]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        body = self.rfile.read(length)
        return json.loads(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.send_json(200, {"status": "ok"})

        elif self.path == "/configs":
            configs = limiter.list_configs()
            self.send_json(200, {"configs": configs})

        elif self.path.startswith("/configs/"):
            name = self.path[9:]
            if "/" in name:
                parts = name.split("/")
                if len(parts) == 2 and parts[1] == "stats":
                    stats = limiter.stats(parts[0])
                    if stats:
                        self.send_json(200, stats)
                    else:
                        self.send_json(404, {"error": "config_not_found"})
                else:
                    self.send_json(404, {"error": "not_found"})
            else:
                config = limiter.get_config(name)
                if config:
                    self.send_json(200, {
                        "name": name,
                        "algorithm": config.algorithm.value,
                        "max_requests": config.max_requests,
                        "window_seconds": config.window_seconds,
                        "burst_size": config.burst_size,
                    })
                else:
                    self.send_json(404, {"error": "config_not_found"})

        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path == "/configs":
            data = self.read_json()
            if not data:
                self.send_json(400, {"error": "missing_body"})
                return

            required = ["name", "algorithm", "max_requests", "window_seconds"]
            if not all(k in data for k in required):
                self.send_json(400, {"error": "missing_fields"})
                return

            try:
                algo = Algorithm(data["algorithm"])
            except ValueError:
                self.send_json(400, {"error": "invalid_algorithm"})
                return

            config = RateLimitConfig(
                algorithm=algo,
                max_requests=int(data["max_requests"]),
                window_seconds=float(data["window_seconds"]),
                burst_size=data.get("burst_size"),
            )
            limiter.configure(data["name"], config)
            self.send_json(201, {"created": data["name"]})

        elif self.path == "/check":
            data = self.read_json()
            if not data or "name" not in data or "key" not in data:
                self.send_json(400, {"error": "missing_fields"})
                return

            result = limiter.check(data["name"], data["key"], data.get("cost", 1))
            status = 200 if "error" not in result else 404
            self.send_json(status, result)

        elif self.path == "/consume":
            data = self.read_json()
            if not data or "name" not in data or "key" not in data:
                self.send_json(400, {"error": "missing_fields"})
                return

            result = limiter.consume(data["name"], data["key"], data.get("cost", 1))
            status = 200 if "error" not in result else 404
            self.send_json(status, result)

        elif self.path == "/reset":
            data = self.read_json()
            if not data or "name" not in data or "key" not in data:
                self.send_json(400, {"error": "missing_fields"})
                return

            success = limiter.reset(data["name"], data["key"])
            if success:
                self.send_json(200, {"reset": True})
            else:
                self.send_json(404, {"error": "config_not_found"})

        else:
            self.send_json(404, {"error": "not_found"})

    def do_DELETE(self) -> None:
        if self.path.startswith("/configs/"):
            name = self.path[9:]
            if limiter.remove_config(name):
                self.send_json(200, {"deleted": name})
            else:
                self.send_json(404, {"error": "config_not_found"})
        else:
            self.send_json(404, {"error": "not_found"})


def main():
    import os
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), RateLimiterHandler)
    print(f"Rate limiter listening on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
