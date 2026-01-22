"""Tests for workspace module."""

import pytest
from pathlib import Path
from unittest.mock import patch
import tempfile
import shutil

from harness.workspace import (
    create_run_id,
    create_workspace,
    get_run_dir,
    save_artifact,
    save_artifact_bytes,
    _generate_test_wrapper,
)


class TestCreateRunId:
    def test_format(self):
        run_id = create_run_id("task", "agent", "model", "variant")
        parts = run_id.split("_")
        assert len(parts) == 6
        assert parts[2] == "task"
        assert parts[3] == "agent"
        assert parts[4] == "model"
        assert parts[5] == "variant"

    def test_timestamp_prefix(self):
        run_id = create_run_id("task", "agent", "model", "variant")
        timestamp = run_id.split("_")[0] + "_" + run_id.split("_")[1]
        assert len(timestamp) == 15  # YYYYMMDD_HHMMSS


class TestCreateWorkspace:
    def test_creates_workspace_directory(self, tmp_path):
        runs_dir = tmp_path / "runs"
        tasks_dir = tmp_path / "tasks"
        task_dir = tasks_dir / "test-task"
        task_dir.mkdir(parents=True)
        
        with patch("harness.workspace.RUNS_DIR", runs_dir):
            with patch("harness.workspace.TASKS_DIR", tasks_dir):
                workspace = create_workspace("test-task", "test-run-id")
                assert workspace.exists()
                assert workspace.is_dir()
                assert (workspace / "run_tests.sh").exists()

    def test_copies_starter_files(self, tmp_path):
        runs_dir = tmp_path / "runs"
        tasks_dir = tmp_path / "tasks"
        task_dir = tasks_dir / "test-task"
        starter_dir = task_dir / "starter"
        starter_dir.mkdir(parents=True)
        (starter_dir / "main.py").write_text("print('hello')")
        
        with patch("harness.workspace.RUNS_DIR", runs_dir):
            with patch("harness.workspace.TASKS_DIR", tasks_dir):
                workspace = create_workspace("test-task", "test-run-id")
                assert (workspace / "main.py").exists()
                assert (workspace / "main.py").read_text() == "print('hello')"

    def test_copies_tests_directory(self, tmp_path):
        runs_dir = tmp_path / "runs"
        tasks_dir = tmp_path / "tasks"
        task_dir = tasks_dir / "test-task"
        task_dir.mkdir(parents=True)
        tests_dir = task_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_api.py").write_text("def test_example(): pass")
        
        with patch("harness.workspace.RUNS_DIR", runs_dir):
            with patch("harness.workspace.TASKS_DIR", tasks_dir):
                workspace = create_workspace("test-task", "test-run-id")
                assert (workspace / "_tests" / "test_api.py").exists()


class TestGenerateTestWrapper:
    def test_creates_executable_script(self, tmp_path):
        _generate_test_wrapper(tmp_path)
        wrapper = tmp_path / "run_tests.sh"
        assert wrapper.exists()
        assert wrapper.stat().st_mode & 0o111  # executable

    def test_script_sets_service_url(self, tmp_path):
        _generate_test_wrapper(tmp_path)
        wrapper = tmp_path / "run_tests.sh"
        content = wrapper.read_text()
        assert "SERVICE_URL" in content
        assert "BASE_URL" in content


class TestSaveArtifact:
    def test_saves_text_artifact(self, tmp_path):
        with patch("harness.workspace.RUNS_DIR", tmp_path):
            save_artifact("test-run", "output.txt", "hello world")
            artifact = tmp_path / "test-run" / "output.txt"
            assert artifact.exists()
            assert artifact.read_text() == "hello world"

    def test_saves_binary_artifact(self, tmp_path):
        with patch("harness.workspace.RUNS_DIR", tmp_path):
            save_artifact_bytes("test-run", "data.bin", b"\x00\x01\x02")
            artifact = tmp_path / "test-run" / "data.bin"
            assert artifact.exists()
            assert artifact.read_bytes() == b"\x00\x01\x02"


class TestGetRunDir:
    def test_returns_correct_path(self, tmp_path):
        with patch("harness.workspace.RUNS_DIR", tmp_path):
            run_dir = get_run_dir("my-run-id")
            assert run_dir == tmp_path / "my-run-id"
