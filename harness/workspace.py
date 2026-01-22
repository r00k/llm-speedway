"""Workspace management for experiment runs."""

import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import TASKS_DIR, RUNS_DIR


def create_run_id(task: str, agent: str, model: str, variant: str) -> str:
    """Generate a unique run ID."""
    import uuid
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    unique = uuid.uuid4().hex[:8]
    return f"{timestamp}_{task}_{agent}_{model}_{variant}_{unique}"


def create_workspace(task: str, run_id: str) -> Path:
    """Create an isolated workspace for an experiment run."""
    run_dir = RUNS_DIR / run_id
    workspace_dir = run_dir / "workspace"
    
    # Create run directory structure
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy starter files to workspace
    starter_dir = TASKS_DIR / task / "starter"
    if starter_dir.exists():
        shutil.copytree(starter_dir, workspace_dir)
    else:
        workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy tests into workspace for agent access
    tests_dir = TASKS_DIR / task / "tests"
    if tests_dir.exists():
        shutil.copytree(tests_dir, workspace_dir / "_tests")
    
    # Generate run_tests.sh wrapper script
    _generate_test_wrapper(workspace_dir)
    
    return workspace_dir


def _generate_test_wrapper(workspace_dir: Path):
    """Generate a run_tests.sh script for the agent to use."""
    # Get absolute path to harness project root for uv
    harness_root = Path(__file__).parent.parent.resolve()
    
    script = f'''#!/bin/bash
# Run tests against your service.
# Your service must be running on the port specified by $PORT (default: 8080).
#
# Usage:
#   ./run_tests.sh              # Run all tests
#   ./run_tests.sh -k "health"  # Run only tests matching "health"
#   ./run_tests.sh -x           # Stop on first failure
#
# The script sets SERVICE_URL automatically based on $PORT.

set -e

PORT="${{PORT:-8080}}"
export SERVICE_URL="http://127.0.0.1:$PORT"
export BASE_URL="$SERVICE_URL"

cd "$(dirname "$0")"

# Run pytest via uv to ensure dependencies are available
uv run --project "{harness_root}" pytest _tests -v --tb=short "$@"
'''
    
    wrapper_path = workspace_dir / "run_tests.sh"
    wrapper_path.write_text(script)
    wrapper_path.chmod(0o755)


def get_run_dir(run_id: str) -> Path:
    """Get the run directory for a run ID."""
    return RUNS_DIR / run_id


def save_artifact(run_id: str, name: str, content: str):
    """Save an artifact to the run directory."""
    run_dir = get_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = run_dir / name
    artifact_path.write_text(content)


def save_artifact_bytes(run_id: str, name: str, content: bytes):
    """Save binary artifact to the run directory."""
    run_dir = get_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = run_dir / name
    artifact_path.write_bytes(content)
