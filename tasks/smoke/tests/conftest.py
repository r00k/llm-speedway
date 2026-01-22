"""Pytest configuration for smoke tests."""

import os
import pytest
import httpx


@pytest.fixture
def base_url() -> str:
    """Get the service base URL from environment."""
    url = os.environ.get("SERVICE_URL") or os.environ.get("BASE_URL")
    if not url:
        pytest.fail("SERVICE_URL or BASE_URL environment variable not set")
    return url.rstrip("/")


@pytest.fixture
def client(base_url: str) -> httpx.Client:
    """Create an HTTP client for the service."""
    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        yield client
