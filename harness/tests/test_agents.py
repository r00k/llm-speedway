"""Tests for agent adapters."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from harness.agents import get_agent, AgentRunner
from harness.agents.base import AgentResult
from harness.agents.codex_cli import CodexCLIRunner
from harness.agents.claude_code import ClaudeCodeRunner
from harness.agents.amp import AmpRunner


class TestGetAgent:
    def test_get_codex(self):
        agent = get_agent("codex")
        assert isinstance(agent, CodexCLIRunner)
        assert agent.name == "codex"

    def test_get_claude_code(self):
        agent = get_agent("claude-code")
        assert isinstance(agent, ClaudeCodeRunner)
        assert agent.name == "claude-code"

    def test_get_amp(self):
        agent = get_agent("amp")
        assert isinstance(agent, AmpRunner)
        assert agent.name == "amp"

    def test_unknown_agent_raises_error(self):
        with pytest.raises(ValueError, match="Unknown agent"):
            get_agent("nonexistent-agent")


class TestAgentResult:
    def test_default_values(self):
        result = AgentResult(exit_code=0, stdout="out", stderr="err")
        assert result.timed_out is False


class TestAgentRunner:
    def test_build_prompt(self):
        agent = get_agent("codex")
        prompt = agent.build_prompt(
            spec="# API Spec",
            system_prompt="You are helpful",
            contract="Must return JSON",
        )
        assert "API Spec" in prompt
        assert "You are helpful" in prompt
        assert "Must return JSON" in prompt
        assert "PORT" in prompt
        assert "/healthz" in prompt
        assert "run.sh" in prompt


class TestCodexCLIRunner:
    def test_run_writes_prompt_file(self, tmp_path):
        runner = CodexCLIRunner()
        
        with patch("harness.agents.codex_cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="output", stderr="", returncode=0
            )
            runner.run(tmp_path, "test prompt", "model", timeout_sec=60)
        
        prompt_file = tmp_path / ".speedway_prompt.md"
        assert prompt_file.exists()
        assert prompt_file.read_text() == "test prompt"

    def test_run_cli_not_found(self, tmp_path):
        runner = CodexCLIRunner()
        
        with patch("harness.agents.codex_cli.subprocess.run", side_effect=FileNotFoundError()):
            result = runner.run(tmp_path, "test prompt", "model", timeout_sec=60)
        
        assert result.exit_code == 127
        assert "not found" in result.stderr

    def test_run_timeout(self, tmp_path):
        runner = CodexCLIRunner()
        
        with patch("harness.agents.codex_cli.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="codex", timeout=60)
            result = runner.run(tmp_path, "test prompt", "model", timeout_sec=60)
        
        assert result.timed_out is True
        assert result.exit_code == -1


class TestClaudeCodeRunner:
    def test_run_writes_prompt_file(self, tmp_path):
        runner = ClaudeCodeRunner()
        
        with patch("harness.agents.claude_code.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="output", stderr="", returncode=0
            )
            runner.run(tmp_path, "test prompt", "opus", timeout_sec=60)
        
        prompt_file = tmp_path / ".speedway_prompt.md"
        assert prompt_file.exists()
        assert prompt_file.read_text() == "test prompt"

    def test_run_cli_not_found(self, tmp_path):
        runner = ClaudeCodeRunner()
        
        with patch("harness.agents.claude_code.subprocess.run", side_effect=FileNotFoundError()):
            result = runner.run(tmp_path, "test prompt", "opus", timeout_sec=60)
        
        assert result.exit_code == 127
        assert "not found" in result.stderr


class TestAmpRunner:
    def test_run_writes_prompt_file(self, tmp_path):
        runner = AmpRunner()
        
        with patch("harness.agents.amp.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="output", stderr="", returncode=0
            )
            runner.run(tmp_path, "test prompt", "smart", timeout_sec=60)
        
        prompt_file = tmp_path / ".speedway_prompt.md"
        assert prompt_file.exists()
        assert prompt_file.read_text() == "test prompt"

    def test_run_cli_not_found(self, tmp_path):
        runner = AmpRunner()
        
        with patch("harness.agents.amp.subprocess.run", side_effect=FileNotFoundError()):
            result = runner.run(tmp_path, "test prompt", "smart", timeout_sec=60)
        
        assert result.exit_code == 127
        assert "not found" in result.stderr
