"""Results storage and analysis."""

import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Literal

from .config import RESULTS_DIR


@dataclass
class ExperimentResult:
    """Result of a single experiment run."""
    run_id: str
    task: str
    agent: str
    model: str
    status: Literal["pass", "fail", "timeout", "error"]
    duration_sec: float
    language: Optional[str] = None
    constraints: Optional[list[str]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "task": self.task,
            "agent": self.agent,
            "model": self.model,
            "language": self.language,
            "constraints": self.constraints,
            "status": self.status,
            "duration_sec": self.duration_sec,
            "error_message": self.error_message,
        }


class ResultsWriter:
    """Writes experiment results to JSONL."""
    
    def __init__(self):
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self.results_file = RESULTS_DIR / "results.jsonl"
    
    def append(self, result: ExperimentResult):
        """Append a result to the results file."""
        with open(self.results_file, "a") as f:
            f.write(json.dumps(result.to_dict()) + "\n")
    
    def load_all(self) -> list[dict]:
        """Load all results."""
        if not self.results_file.exists():
            return []
        
        results = []
        with open(self.results_file) as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
        return results


def save_run_result(run_id: str, result: ExperimentResult):
    """Save result to both run directory and global results."""
    from .workspace import get_run_dir
    
    # Save to run directory
    run_dir = get_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    result_file = run_dir / "result.json"
    result_file.write_text(json.dumps(result.to_dict(), indent=2))
    
    # Append to global results
    writer = ResultsWriter()
    writer.append(result)
