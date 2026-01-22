"""Tests for run_all module."""

import pytest
from unittest.mock import patch, MagicMock

from harness.run_all import AGENTS, run_experiment, main


class TestAgentsConfig:
    def test_agents_has_three_entries(self):
        assert len(AGENTS) == 3

    def test_agents_have_correct_structure(self):
        for agent, model in AGENTS:
            assert isinstance(agent, str)
            assert isinstance(model, str)

    def test_agents_include_expected_agents(self):
        agent_names = [a for a, _ in AGENTS]
        assert "amp" in agent_names
        assert "claude-code" in agent_names
        assert "codex" in agent_names


class TestRunExperiment:
    @patch("harness.run_all.subprocess.run")
    def test_run_experiment_builds_correct_command(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        
        agent, success = run_experiment(
            task="test-task",
            agent="amp",
            model="smart",
            language=None,
            constraints=None,
        )
        
        assert agent == "amp"
        assert success is True
        
        call_args = mock_run.call_args[0][0]
        assert "--task" in call_args
        assert "test-task" in call_args
        assert "--agent" in call_args
        assert "amp" in call_args
        assert "--model" in call_args
        assert "smart" in call_args

    @patch("harness.run_all.subprocess.run")
    def test_run_experiment_with_language(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        
        run_experiment(
            task="test-task",
            agent="amp",
            model="smart",
            language="Go",
            constraints=None,
        )
        
        call_args = mock_run.call_args[0][0]
        assert "--language" in call_args
        assert "Go" in call_args

    @patch("harness.run_all.subprocess.run")
    def test_run_experiment_with_constraints(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        
        run_experiment(
            task="test-task",
            agent="amp",
            model="smart",
            language=None,
            constraints=["use only 5 files", "no deps"],
        )
        
        call_args = mock_run.call_args[0][0]
        assert call_args.count("--constraint") == 2
        assert "use only 5 files" in call_args
        assert "no deps" in call_args

    @patch("harness.run_all.subprocess.run")
    def test_run_experiment_returns_failure_on_nonzero_exit(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        
        agent, success = run_experiment(
            task="test-task",
            agent="codex",
            model="codex-5.2",
            language=None,
            constraints=None,
        )
        
        assert agent == "codex"
        assert success is False


class TestMain:
    @patch("harness.run_all.run_experiment")
    def test_main_runs_all_agents_by_default(self, mock_run):
        mock_run.return_value = ("agent", True)
        
        with patch("sys.argv", ["run_all", "--task", "test-task"]):
            main()
        
        assert mock_run.call_count == 3

    @patch("harness.run_all.run_experiment")
    def test_main_filters_agents(self, mock_run):
        mock_run.return_value = ("agent", True)
        
        with patch("sys.argv", ["run_all", "--task", "test-task", "--agents", "amp", "codex"]):
            main()
        
        assert mock_run.call_count == 2
        called_agents = [call[0][1] for call in mock_run.call_args_list]
        assert "amp" in called_agents
        assert "codex" in called_agents
        assert "claude-code" not in called_agents

    @patch("harness.run_all.run_experiment")
    def test_main_passes_language_and_constraints(self, mock_run):
        mock_run.return_value = ("agent", True)
        
        with patch("sys.argv", [
            "run_all", "--task", "test-task",
            "--language", "Rust",
            "--constraint", "no deps",
            "--agents", "amp",
        ]):
            main()
        
        call_args = mock_run.call_args_list[0][0]
        assert call_args[3] == "Rust"  # language
        assert call_args[4] == ["no deps"]  # constraints
