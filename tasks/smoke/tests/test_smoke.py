"""Smoke tests for the minimal service."""

import pytest
import httpx


def test_healthz(client: httpx.Client):
    """Test that /healthz returns ok."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_echo_with_message(client: httpx.Client):
    """Test that /echo returns the message."""
    resp = client.get("/echo", params={"message": "hello world"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "hello world"


def test_echo_missing_message(client: httpx.Client):
    """Test that /echo returns 400 when message is missing."""
    resp = client.get("/echo")
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
