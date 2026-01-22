"""
Black-box HTTP tests for the Rate Limiter service.
These tests work against any implementation regardless of language.

Uses httpx client fixture from conftest.py - URL is injected via environment.
"""
import time
import pytest


@pytest.fixture(autouse=True)
def cleanup(client):
    """Clean up any configs created during tests."""
    yield
    # Try to delete common test configs
    for name in ["test-limit", "sw-limit", "tb-limit", "multi-key", "cost-test"]:
        try:
            client.delete(f"/configs/{name}", timeout=2)
        except Exception:
            pass


class TestHealthCheck:
    def test_healthz(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestConfigManagement:
    def test_create_config_sliding_window(self, client):
        r = client.post("/configs", json={
            "name": "test-limit",
            "algorithm": "sliding_window",
            "max_requests": 10,
            "window_seconds": 60
        })
        assert r.status_code == 201
        assert r.json()["created"] == "test-limit"

    def test_create_config_token_bucket(self, client):
        r = client.post("/configs", json={
            "name": "test-limit",
            "algorithm": "token_bucket",
            "max_requests": 10,
            "window_seconds": 60,
            "burst_size": 15
        })
        assert r.status_code == 201
        assert r.json()["created"] == "test-limit"

    def test_create_config_missing_fields(self, client):
        r = client.post("/configs", json={
            "name": "test-limit"
        })
        assert r.status_code == 400
        assert r.json()["error"] == "missing_fields"

    def test_create_config_invalid_algorithm(self, client):
        r = client.post("/configs", json={
            "name": "test-limit",
            "algorithm": "invalid",
            "max_requests": 10,
            "window_seconds": 60
        })
        assert r.status_code == 400
        assert r.json()["error"] == "invalid_algorithm"

    def test_list_configs(self, client):
        client.post("/configs", json={
            "name": "test-limit",
            "algorithm": "sliding_window",
            "max_requests": 10,
            "window_seconds": 60
        })
        r = client.get("/configs")
        assert r.status_code == 200
        assert "test-limit" in r.json()["configs"]

    def test_get_config(self, client):
        client.post("/configs", json={
            "name": "test-limit",
            "algorithm": "sliding_window",
            "max_requests": 10,
            "window_seconds": 60
        })
        r = client.get("/configs/test-limit")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "test-limit"
        assert data["algorithm"] == "sliding_window"
        assert data["max_requests"] == 10
        assert data["window_seconds"] == 60

    def test_get_config_not_found(self, client):
        r = client.get("/configs/nonexistent")
        assert r.status_code == 404
        assert r.json()["error"] == "config_not_found"

    def test_delete_config(self, client):
        client.post("/configs", json={
            "name": "test-limit",
            "algorithm": "sliding_window",
            "max_requests": 10,
            "window_seconds": 60
        })
        r = client.delete("/configs/test-limit")
        assert r.status_code == 200
        assert r.json()["deleted"] == "test-limit"

        r = client.get("/configs/test-limit")
        assert r.status_code == 404

    def test_delete_config_not_found(self, client):
        r = client.delete("/configs/nonexistent")
        assert r.status_code == 404

    def test_get_stats(self, client):
        client.post("/configs", json={
            "name": "test-limit",
            "algorithm": "sliding_window",
            "max_requests": 10,
            "window_seconds": 60
        })
        # Make some requests to create active keys
        client.post("/consume", json={
            "name": "test-limit", "key": "user-1"
        })
        client.post("/consume", json={
            "name": "test-limit", "key": "user-2"
        })

        r = client.get("/configs/test-limit/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "test-limit"
        assert data["algorithm"] == "sliding_window"
        assert data["active_keys"] == 2


class TestSlidingWindow:
    @pytest.fixture(autouse=True)
    def setup_config(self, client):
        client.post("/configs", json={
            "name": "sw-limit",
            "algorithm": "sliding_window",
            "max_requests": 5,
            "window_seconds": 10
        })

    def test_check_without_consuming(self, client):
        r = client.post("/check", json={
            "name": "sw-limit", "key": "user-1"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["allowed"] is True
        assert data["remaining"] == 5
        assert data["limit"] == 5
        assert data["algorithm"] == "sliding_window"

        # Check again - should still be 5 (not consumed)
        r = client.post("/check", json={
            "name": "sw-limit", "key": "user-1"
        })
        assert r.json()["remaining"] == 5

    def test_consume_decrements(self, client):
        r = client.post("/consume", json={
            "name": "sw-limit", "key": "user-1"
        })
        assert r.status_code == 200
        assert r.json()["allowed"] is True
        assert r.json()["remaining"] == 4

        r = client.post("/consume", json={
            "name": "sw-limit", "key": "user-1"
        })
        assert r.json()["remaining"] == 3

    def test_exceeds_limit(self, client):
        # Consume all 5 requests
        for _ in range(5):
            r = client.post("/consume", json={
                "name": "sw-limit", "key": "user-1"
            })
            assert r.json()["allowed"] is True

        # 6th should be denied
        r = client.post("/consume", json={
            "name": "sw-limit", "key": "user-1"
        })
        assert r.json()["allowed"] is False
        assert r.json()["remaining"] == 0

    def test_keys_are_isolated(self, client):
        # Exhaust user-1
        for _ in range(5):
            client.post("/consume", json={
                "name": "sw-limit", "key": "user-1"
            })

        # user-2 should still have full quota
        r = client.post("/check", json={
            "name": "sw-limit", "key": "user-2"
        })
        assert r.json()["allowed"] is True
        assert r.json()["remaining"] == 5

    def test_reset_key(self, client):
        # Consume some
        for _ in range(3):
            client.post("/consume", json={
                "name": "sw-limit", "key": "user-1"
            })

        # Reset
        r = client.post("/reset", json={
            "name": "sw-limit", "key": "user-1"
        })
        assert r.status_code == 200
        assert r.json()["reset"] is True

        # Should have full quota again
        r = client.post("/check", json={
            "name": "sw-limit", "key": "user-1"
        })
        assert r.json()["remaining"] == 5

    def test_cost_parameter(self, client):
        # Check with cost=3
        r = client.post("/check", json={
            "name": "sw-limit", "key": "user-1", "cost": 3
        })
        assert r.json()["allowed"] is True

        # Consume with cost=3
        r = client.post("/consume", json={
            "name": "sw-limit", "key": "user-1", "cost": 3
        })
        assert r.json()["allowed"] is True
        assert r.json()["remaining"] == 2

        # Try to consume 3 more (should fail, only 2 remaining)
        r = client.post("/consume", json={
            "name": "sw-limit", "key": "user-1", "cost": 3
        })
        assert r.json()["allowed"] is False


class TestTokenBucket:
    @pytest.fixture(autouse=True)
    def setup_config(self, client):
        client.post("/configs", json={
            "name": "tb-limit",
            "algorithm": "token_bucket",
            "max_requests": 10,  # 10 tokens per 10 seconds = 1/sec refill
            "window_seconds": 10,
            "burst_size": 5
        })

    def test_initial_tokens_equal_burst_size(self, client):
        r = client.post("/check", json={
            "name": "tb-limit", "key": "user-1"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["allowed"] is True
        assert data["remaining"] == 5  # burst_size
        assert data["limit"] == 5
        assert data["algorithm"] == "token_bucket"

    def test_consume_decrements_tokens(self, client):
        r = client.post("/consume", json={
            "name": "tb-limit", "key": "user-1"
        })
        assert r.json()["allowed"] is True
        assert r.json()["remaining"] == 4

    def test_burst_then_throttle(self, client):
        # Consume all 5 burst tokens
        for i in range(5):
            r = client.post("/consume", json={
                "name": "tb-limit", "key": "user-1"
            })
            assert r.json()["allowed"] is True

        # Next request should be denied (no tokens left)
        r = client.post("/consume", json={
            "name": "tb-limit", "key": "user-1"
        })
        assert r.json()["allowed"] is False
        assert r.json()["remaining"] == 0

    def test_tokens_refill_over_time(self, client):
        # Consume all tokens
        for _ in range(5):
            client.post("/consume", json={
                "name": "tb-limit", "key": "user-1"
            })

        # Wait for refill (1 token/second, wait 1.5 seconds for safety)
        time.sleep(1.5)

        # Should have ~1 token now
        r = client.post("/check", json={
            "name": "tb-limit", "key": "user-1"
        })
        assert r.json()["allowed"] is True
        assert r.json()["remaining"] >= 1

    def test_burst_size_defaults_to_max_requests(self, client):
        client.post("/configs", json={
            "name": "tb-default",
            "algorithm": "token_bucket",
            "max_requests": 20,
            "window_seconds": 10
            # no burst_size specified
        })

        r = client.get("/configs/tb-default")
        assert r.json()["burst_size"] == 20

        r = client.post("/check", json={
            "name": "tb-default", "key": "user-1"
        })
        assert r.json()["remaining"] == 20

        # Cleanup
        client.delete("/configs/tb-default")

    def test_cost_parameter(self, client):
        r = client.post("/consume", json={
            "name": "tb-limit", "key": "user-1", "cost": 3
        })
        assert r.json()["allowed"] is True
        assert r.json()["remaining"] == 2

        # Try to consume 3 more (only 2 remaining)
        r = client.post("/consume", json={
            "name": "tb-limit", "key": "user-1", "cost": 3
        })
        assert r.json()["allowed"] is False


class TestErrorHandling:
    def test_check_unknown_config(self, client):
        r = client.post("/check", json={
            "name": "nonexistent", "key": "user-1"
        })
        assert r.status_code == 404
        assert r.json()["error"] == "config_not_found"

    def test_consume_unknown_config(self, client):
        r = client.post("/consume", json={
            "name": "nonexistent", "key": "user-1"
        })
        assert r.status_code == 404
        assert r.json()["error"] == "config_not_found"

    def test_reset_unknown_config(self, client):
        r = client.post("/reset", json={
            "name": "nonexistent", "key": "user-1"
        })
        assert r.status_code == 404
        assert r.json()["error"] == "config_not_found"

    def test_check_missing_fields(self, client):
        r = client.post("/check", json={"name": "test"})
        assert r.status_code == 400
        assert r.json()["error"] == "missing_fields"

    def test_consume_missing_fields(self, client):
        r = client.post("/consume", json={"key": "user-1"})
        assert r.status_code == 400
        assert r.json()["error"] == "missing_fields"

    def test_unknown_endpoint(self, client):
        r = client.get("/unknown")
        assert r.status_code == 404

        r = client.post("/unknown", json={})
        assert r.status_code == 404


class TestMultipleConfigs:
    def test_multiple_configs_isolated(self, client):
        # Create two different configs
        client.post("/configs", json={
            "name": "config-a",
            "algorithm": "sliding_window",
            "max_requests": 3,
            "window_seconds": 60
        })
        client.post("/configs", json={
            "name": "config-b",
            "algorithm": "sliding_window",
            "max_requests": 100,
            "window_seconds": 60
        })

        # Exhaust config-a for user-1
        for _ in range(3):
            client.post("/consume", json={
                "name": "config-a", "key": "user-1"
            })

        # config-b should still allow
        r = client.post("/check", json={
            "name": "config-b", "key": "user-1"
        })
        assert r.json()["allowed"] is True
        assert r.json()["remaining"] == 100

        # Cleanup
        client.delete("/configs/config-a")
        client.delete("/configs/config-b")
