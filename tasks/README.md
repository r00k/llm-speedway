# Creating Tasks

Each task is a self-contained benchmark that agents must implement.

## Directory Structure

```
tasks/
  my-task/
    harness.yaml      # Task configuration
    SPEC.md           # Specification given to agents
    starter/          # Files copied to agent workspace (optional)
    tests/            # Black-box HTTP tests
      conftest.py     # Required: fixtures for HTTP client
      test_*.py       # Test files using fixtures
```

## harness.yaml

```yaml
port: 8080
timeout_minutes: 60
healthz_path: /healthz
healthz_timeout_sec: 120
spec_file: SPEC.md
```

## Writing Tests

**IMPORTANT:** Tests must use the `client` fixture pattern, not module-level URL constants.

### Required: conftest.py

Every task with HTTP tests needs this `conftest.py`:

```python
"""Pytest configuration and fixtures."""

import os
import pytest
import httpx

# URL is injected via environment by the test runner
BASE_URL = os.environ.get("SERVICE_URL", os.environ.get("BASE_URL", "http://127.0.0.1:8080"))


@pytest.fixture(scope="session")
def base_url():
    """Get the base URL for the service."""
    return BASE_URL


@pytest.fixture(scope="session")
def client(base_url):
    """Create an HTTP client for the service."""
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def fresh_client(base_url):
    """Create a fresh HTTP client (for tests that need isolation)."""
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        yield client
```

### Test Files

Tests must accept `client` as a fixture parameter:

```python
# ✅ CORRECT: Uses fixture injection
def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


class TestFeature:
    def test_create(self, client):
        r = client.post("/items", json={"name": "test"})
        assert r.status_code == 201
```

### Why This Pattern?

The harness runs tests via subprocess with dynamic ports:

1. `ServiceManager` starts the service on a random free port
2. `SuiteRunner` runs pytest with `BASE_URL=http://127.0.0.1:{port}` in the environment
3. Tests read the URL from the environment

**The failure mode:** If you use module-level constants like:

```python
# ❌ WRONG: Evaluated at import time, before env vars are set
import requests
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")

def test_healthz():
    r = requests.get(f"{BASE_URL}/healthz")  # Always hits port 8080!
```

This evaluates `BASE_URL` when Python imports the module, which happens before the subprocess passes the environment variables. The fixture pattern defers URL resolution until test collection time.

## Test Dependencies

Tests can use `httpx` and `pytest` - both are available via the harness's uv environment. Don't use `requests`.
