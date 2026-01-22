"""Tests for service module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from harness.service import ServiceManager


class TestServiceManager:
    def test_base_url(self, tmp_path):
        mgr = ServiceManager(tmp_path, port=3000)
        assert mgr.base_url == "http://127.0.0.1:3000"

    def test_default_values(self, tmp_path):
        mgr = ServiceManager(tmp_path, port=8080)
        assert mgr.healthz_path == "/healthz"
        assert mgr.healthz_timeout_sec == 120

    def test_start_missing_run_script(self, tmp_path):
        mgr = ServiceManager(tmp_path, port=8080)
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        
        with pytest.raises(FileNotFoundError, match="run.sh not found"):
            mgr.start(run_dir)

    def test_is_running_no_process(self, tmp_path):
        mgr = ServiceManager(tmp_path, port=8080)
        assert mgr.is_running() is False

    def test_stop_no_process(self, tmp_path):
        mgr = ServiceManager(tmp_path, port=8080)
        mgr.stop()  # Should not raise
