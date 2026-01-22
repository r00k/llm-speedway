# Language Rewrite: Rate Limiter Service

Rewrite the provided Python rate limiter service in **{{LANGUAGE}}**.

## Source Code

The complete Python implementation is provided in `starter/rate_limiter.py`. Your task is to produce a functionally equivalent implementation in {{LANGUAGE}}.

## Overview

The rate limiter service provides HTTP APIs for managing and enforcing rate limits using two algorithms:

1. **Sliding Window**: Counts requests within a rolling time window
2. **Token Bucket**: Refills tokens at a steady rate, allows bursts up to bucket size

## API Specification

### Health Check

```
GET /healthz
Response: {"status": "ok"}
```

### Configuration Management

**Create/Update Config**
```
POST /configs
Body: {
  "name": "api-limit",
  "algorithm": "sliding_window" | "token_bucket",
  "max_requests": 100,
  "window_seconds": 60,
  "burst_size": 150  // optional, token_bucket only
}
Response: 201 {"created": "api-limit"}
```

**List Configs**
```
GET /configs
Response: {"configs": ["api-limit", "login-limit"]}
```

**Get Config**
```
GET /configs/{name}
Response: {
  "name": "api-limit",
  "algorithm": "sliding_window",
  "max_requests": 100,
  "window_seconds": 60,
  "burst_size": null
}
Response: 404 {"error": "config_not_found"}
```

**Delete Config**
```
DELETE /configs/{name}
Response: 200 {"deleted": "api-limit"}
Response: 404 {"error": "config_not_found"}
```

**Get Stats**
```
GET /configs/{name}/stats
Response: {
  "name": "api-limit",
  "algorithm": "sliding_window",
  "active_keys": 42,
  "config": {...}
}
```

### Rate Limiting Operations

**Check Limit (without consuming)**
```
POST /check
Body: {"name": "api-limit", "key": "user-123", "cost": 1}
Response: {
  "allowed": true,
  "remaining": 95,
  "limit": 100,
  "reset_at": 1699900000.0,
  "algorithm": "sliding_window"
}
```

**Consume (check and decrement)**
```
POST /consume
Body: {"name": "api-limit", "key": "user-123", "cost": 1}
Response: {
  "allowed": true,
  "remaining": 94,
  "limit": 100,
  "reset_at": 1699900000.0,
  "algorithm": "sliding_window"
}
```

**Reset Key**
```
POST /reset
Body: {"name": "api-limit", "key": "user-123"}
Response: 200 {"reset": true}
Response: 404 {"error": "config_not_found"}
```

## Algorithm Details

### Sliding Window

- Maintains list of request timestamps per key
- On check/consume: removes timestamps older than `window_seconds`
- Request allowed if `count + cost <= max_requests`
- `remaining` = `max_requests - current_count`
- `reset_at` = `now + window_seconds`

### Token Bucket

- Each key has a bucket with `tokens` (float) and `last_refill` timestamp
- Refill rate = `max_requests / window_seconds` tokens per second
- On check/consume: refill tokens based on elapsed time, cap at `burst_size`
- Request allowed if `tokens >= cost`
- Consume decrements tokens by cost
- `remaining` = `floor(tokens)`
- `burst_size` defaults to `max_requests` if not specified

## Requirements

1. **Functional equivalence**: All API endpoints must behave identically
2. **Thread safety**: Must handle concurrent requests correctly
3. **In-memory storage**: No external database required
4. **Port**: Read from `PORT` environment variable, default 8080
5. **No external dependencies**: Use only {{LANGUAGE}} standard library

## Verification

Your implementation will be tested with the same black-box HTTP test suite used to validate the Python version. Tests cover:

- Configuration CRUD operations
- Sliding window rate limiting behavior
- Token bucket rate limiting with bursts
- Multi-key isolation
- Cost parameter handling
- Edge cases and error responses

## Running

Create a `run.sh` script that builds (if needed) and starts your server:

```bash
#!/bin/bash
# Example for Go:
# go build -o server . && ./server

# Example for Rust:
# cargo build --release && ./target/release/rate_limiter

# Example for TypeScript:
# npx tsx server.ts
```

## Hints

- Study the Python implementation carefully—edge cases matter
- Pay attention to float vs int handling in token bucket
- The `reset_at` calculation differs between algorithms
- Thread safety is required for correctness under load
