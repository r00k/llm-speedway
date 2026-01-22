"""Configuration loading for harness."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import yaml


ROOT_DIR = Path(__file__).parent.parent
TASKS_DIR = ROOT_DIR / "tasks"
PROMPTS_DIR = ROOT_DIR / "prompts"
RUNS_DIR = ROOT_DIR / "runs"
RESULTS_DIR = ROOT_DIR / "results"


@dataclass
class TaskConfig:
    """Configuration for a benchmark task."""
    name: str
    port: int = 8080
    timeout_minutes: int = 60
    healthz_path: str = "/healthz"
    healthz_timeout_sec: int = 120
    spec_file: str = "SPEC.md"
    
    @classmethod
    def load(cls, task_name: str) -> "TaskConfig":
        task_dir = TASKS_DIR / task_name
        config_file = task_dir / "harness.yaml"
        
        if config_file.exists():
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
            return cls(name=task_name, **data)
        
        return cls(name=task_name)


@dataclass
class AgentConfig:
    """Configuration for an agent adapter."""
    name: str
    command: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    timeout_minutes: int = 60
    

def get_prompt_variant(variant: str) -> str:
    """Load a system prompt variant."""
    prompt_file = PROMPTS_DIR / "system" / f"{variant}.md"
    if not prompt_file.exists():
        raise ValueError(f"Prompt variant not found: {variant}")
    return prompt_file.read_text()


def get_task_wrapper() -> str:
    """Load the HTTP service contract wrapper."""
    wrapper_file = PROMPTS_DIR / "task_wrappers" / "http-service-contract.md"
    return wrapper_file.read_text()


def get_spec(task_name: str) -> str:
    """Load the spec for a task."""
    task_config = TaskConfig.load(task_name)
    spec_file = TASKS_DIR / task_name / task_config.spec_file
    return spec_file.read_text()
