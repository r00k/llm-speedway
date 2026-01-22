"""Test runner for validating service implementations."""

import subprocess
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from .config import TASKS_DIR


@dataclass
class TestResult:
    """Result of running tests."""
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    tests_passed: int = 0
    tests_failed: int = 0
    tests_total: int = 0


class TestRunner:
    """Runs the test suite against a service."""
    
    def __init__(self, task: str, base_url: str):
        self.task = task
        self.base_url = base_url
        self.tests_dir = TASKS_DIR / task / "tests"
    
    def run(self, run_dir: Optional[Path] = None, timeout_sec: int = 300) -> TestResult:
        """Run the test suite."""
        
        if not self.tests_dir.exists():
            return TestResult(
                passed=False,
                exit_code=1,
                stdout="",
                stderr=f"Tests directory not found: {self.tests_dir}",
            )
        
        # Set up environment
        env = os.environ.copy()
        env["SERVICE_URL"] = self.base_url
        env["BASE_URL"] = self.base_url
        
        # Run pytest via uv to ensure dependencies (httpx, pytest) are available
        cmd = [
            "uv", "run", "--project", str(TASKS_DIR.parent),
            "pytest",
            str(self.tests_dir),
            "-v",
            "--tb=short",
            "-x",  # Stop on first failure for speed measurement
        ]
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode
            
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout.decode() if e.stdout else ""
            stderr = e.stderr.decode() if e.stderr else "Tests timed out"
            exit_code = -1
        
        # Parse test counts from pytest output
        tests_passed, tests_failed, tests_total = self._parse_pytest_output(stdout)
        
        # Save logs
        if run_dir:
            (run_dir / "test.stdout.log").write_text(stdout)
            (run_dir / "test.stderr.log").write_text(stderr)
        
        return TestResult(
            passed=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            tests_total=tests_total,
        )
    
    def _parse_pytest_output(self, output: str) -> tuple[int, int, int]:
        """Parse pytest output to extract test counts."""
        # Look for summary line like "5 passed, 2 failed"
        import re
        
        passed = 0
        failed = 0
        
        # Match patterns like "5 passed" or "2 failed"
        passed_match = re.search(r"(\d+) passed", output)
        failed_match = re.search(r"(\d+) failed", output)
        
        if passed_match:
            passed = int(passed_match.group(1))
        if failed_match:
            failed = int(failed_match.group(1))
        
        return passed, failed, passed + failed
