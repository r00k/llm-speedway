"""Pytest configuration and fixtures for rate limiter tests."""

import os
import pytest
import httpx

# Centralized URL configuration - reads from env vars set by test runner
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
