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
    mode: str = "standard"  # "standard" or "self-testing"
    template_vars: dict = field(default_factory=dict)
    starter_files: list = field(default_factory=list)
    
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
    

def get_system_prompt(language: str | None = None, constraints: list[str] | None = None) -> str:
    """Build system prompt with optional language and constraints.
    
    Args:
        language: Force a specific language (e.g., "Go", "Python")
        constraints: Natural language constraints like "use only 5 files"
    """
    base_prompt = (PROMPTS_DIR / "system" / "default.md").read_text()
    
    blocks = []
    
    if language:
        blocks.append(f"""## CRITICAL: Use {language}

You MUST implement this service in {language}.
- Use idiomatic {language} patterns and best practices
- Use appropriate libraries for HTTP server and database""")
    
    if constraints:
        constraint_text = "## CRITICAL: Constraints\n\nYou MUST follow these constraints:\n"
        for c in constraints:
            constraint_text += f"- {c}\n"
        blocks.append(constraint_text)
    
    if not blocks:
        return base_prompt
    
    # Insert after first heading
    lines = base_prompt.split('\n')
    insert_idx = 1
    for i, line in enumerate(lines):
        if line.startswith('# '):
            insert_idx = i + 1
            break
    lines.insert(insert_idx, '\n' + '\n'.join(blocks))
    return '\n'.join(lines)


def get_task_wrapper(mode: str = "standard") -> str:
    """Load the HTTP service contract wrapper.
    
    Args:
        mode: "standard" (tests provided) or "self-testing" (model writes tests)
    """
    if mode == "self-testing":
        wrapper_file = PROMPTS_DIR / "task_wrappers" / "http-service-self-testing.md"
    else:
        wrapper_file = PROMPTS_DIR / "task_wrappers" / "http-service-contract.md"
    return wrapper_file.read_text()


def get_spec(task_name: str, language: str | None = None) -> str:
    """Load the spec for a task, substituting template variables.
    
    Supports {{LANGUAGE}} placeholder which is replaced with the --language arg.
    """
    task_config = TaskConfig.load(task_name)
    spec_file = TASKS_DIR / task_name / task_config.spec_file
    content = spec_file.read_text()
    
    if language:
        content = content.replace("{{LANGUAGE}}", language)
    else:
        content = content.replace("{{LANGUAGE}}", "a language of your choice")
    
    return content
