"""Tests for test_runner module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from harness.test_runner import TestRunner, TestResult


class TestTestResult:
    def test_default_values(self):
        result = TestResult(
            passed=True,
            exit_code=0,
            stdout="output",
            stderr="",
        )
        assert result.tests_passed == 0
        assert result.tests_failed == 0
        assert result.tests_total == 0
        assert result.failed_tests == []


class TestTestRunner:
    def test_missing_tests_dir(self, tmp_path):
        with patch("harness.test_runner.TASKS_DIR", tmp_path):
            runner = TestRunner("nonexistent", "http://localhost:8080")
            result = runner.run()
            assert not result.passed
            assert "not found" in result.stderr

    def test_parse_pytest_output_passed_only(self):
        runner = TestRunner("task", "http://localhost:8080")
        passed, failed, total = runner._parse_pytest_output("5 passed in 1.23s")
        assert passed == 5
        assert failed == 0
        assert total == 5

    def test_parse_pytest_output_mixed(self):
        runner = TestRunner("task", "http://localhost:8080")
        passed, failed, total = runner._parse_pytest_output("3 passed, 2 failed in 2.5s")
        assert passed == 3
        assert failed == 2
        assert total == 5

    def test_parse_pytest_output_failed_only(self):
        runner = TestRunner("task", "http://localhost:8080")
        passed, failed, total = runner._parse_pytest_output("4 failed in 0.5s")
        assert passed == 0
        assert failed == 4
        assert total == 4

    def test_parse_pytest_output_no_results(self):
        runner = TestRunner("task", "http://localhost:8080")
        passed, failed, total = runner._parse_pytest_output("no tests ran")
        assert passed == 0
        assert failed == 0
        assert total == 0

    def test_parse_failed_tests_single(self):
        runner = TestRunner("task", "http://localhost:8080")
        output = "tests/test_foo.py::test_bar FAILED"
        failed = runner._parse_failed_tests(output)
        assert failed == ["tests/test_foo.py::test_bar"]

    def test_parse_failed_tests_multiple(self):
        runner = TestRunner("task", "http://localhost:8080")
        output = """
tests/test_foo.py::test_one PASSED
tests/test_foo.py::test_two FAILED
tests/test_bar.py::test_three FAILED
tests/test_bar.py::test_four PASSED
"""
        failed = runner._parse_failed_tests(output)
        assert failed == ["tests/test_foo.py::test_two", "tests/test_bar.py::test_three"]

    def test_parse_failed_tests_none(self):
        runner = TestRunner("task", "http://localhost:8080")
        output = "5 passed in 1.23s"
        failed = runner._parse_failed_tests(output)
        assert failed == []
