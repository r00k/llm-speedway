"""Tests for config module."""

import pytest
from pathlib import Path
import tempfile
import shutil

from harness.config import (
    TaskConfig,
    TASKS_DIR,
    PROMPTS_DIR,
    get_system_prompt,
    get_task_wrapper,
    get_spec,
)


class TestTaskConfig:
    def test_default_values(self):
        config = TaskConfig(name="test-task")
        assert config.name == "test-task"
        assert config.port == 8080
        assert config.timeout_minutes == 60
        assert config.healthz_path == "/healthz"
        assert config.healthz_timeout_sec == 120
        assert config.spec_file == "SPEC.md"

    def test_custom_values(self):
        config = TaskConfig(
            name="custom",
            port=3000,
            timeout_minutes=30,
            healthz_path="/health",
            healthz_timeout_sec=60,
            spec_file="spec.md",
        )
        assert config.port == 3000
        assert config.timeout_minutes == 30
        assert config.healthz_path == "/health"

    def test_load_missing_task_returns_defaults(self):
        config = TaskConfig.load("nonexistent-task-12345")
        assert config.name == "nonexistent-task-12345"
        assert config.port == 8080


class TestGetSystemPrompt:
    def test_no_constraints_returns_base(self):
        prompt = get_system_prompt()
        assert "expert software engineer" in prompt
    
    def test_language_constraint(self):
        prompt = get_system_prompt(language="Go")
        assert "CRITICAL: Use Go" in prompt
        assert "idiomatic Go" in prompt
    
    def test_custom_constraints(self):
        prompt = get_system_prompt(constraints=["use only 5 files", "no external deps"])
        assert "CRITICAL: Constraints" in prompt
        assert "use only 5 files" in prompt
        assert "no external deps" in prompt
    
    def test_both_language_and_constraints(self):
        prompt = get_system_prompt(language="Rust", constraints=["keep it simple"])
        assert "CRITICAL: Use Rust" in prompt
        assert "keep it simple" in prompt


class TestGetSpec:
    def test_missing_task_raises_error(self):
        with pytest.raises(FileNotFoundError):
            get_spec("nonexistent-task-12345")
