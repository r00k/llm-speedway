"""Tests for results module."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from harness.results import ExperimentResult, ResultsWriter


class TestExperimentResult:
    def test_to_dict(self):
        result = ExperimentResult(
            run_id="test-run",
            task="test-task",
            agent="test-agent",
            model="test-model",
            status="pass",
            duration_sec=123.45,
        )
        d = result.to_dict()
        assert d["run_id"] == "test-run"
        assert d["task"] == "test-task"
        assert d["agent"] == "test-agent"
        assert d["model"] == "test-model"
        assert d["language"] is None
        assert d["constraints"] is None
        assert d["status"] == "pass"
        assert d["duration_sec"] == 123.45
        assert d["error_message"] is None

    def test_to_dict_with_constraints(self):
        result = ExperimentResult(
            run_id="test-run",
            task="test-task",
            agent="test-agent",
            model="test-model",
            status="pass",
            duration_sec=100.0,
            language="Go",
            constraints=["use only 5 files"],
        )
        d = result.to_dict()
        assert d["language"] == "Go"
        assert d["constraints"] == ["use only 5 files"]

    def test_to_dict_with_error(self):
        result = ExperimentResult(
            run_id="test-run",
            task="test-task",
            agent="test-agent",
            model="test-model",
            status="error",
            duration_sec=10.0,
            error_message="Something went wrong",
        )
        d = result.to_dict()
        assert d["status"] == "error"
        assert d["error_message"] == "Something went wrong"


class TestResultsWriter:
    def test_append_and_load(self, tmp_path):
        with patch("harness.results.RESULTS_DIR", tmp_path):
            writer = ResultsWriter()
            
            result1 = ExperimentResult(
                run_id="run-1",
                task="task-1",
                agent="agent-1",
                model="model-1",
                status="pass",
                duration_sec=100.0,
            )
            result2 = ExperimentResult(
                run_id="run-2",
                task="task-2",
                agent="agent-2",
                model="model-2",
                status="fail",
                duration_sec=200.0,
            )
            
            writer.append(result1)
            writer.append(result2)
            
            loaded = writer.load_all()
            assert len(loaded) == 2
            assert loaded[0]["run_id"] == "run-1"
            assert loaded[1]["run_id"] == "run-2"

    def test_load_empty(self, tmp_path):
        with patch("harness.results.RESULTS_DIR", tmp_path):
            writer = ResultsWriter()
            loaded = writer.load_all()
            assert loaded == []
