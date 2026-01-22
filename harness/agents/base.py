"""Base class for agent adapters."""

from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentResult:
    """Result of running an agent."""
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class AgentRunner(ABC):
    """Base class for agent adapters."""
    
    name: str = "base"
    
    @abstractmethod
    def run(
        self,
        workspace_dir: Path,
        prompt: str,
        model: str,
        timeout_sec: int = 3600,
        run_dir: Optional[Path] = None,
    ) -> AgentResult:
        """
        Run the agent in the given workspace.
        
        Args:
            workspace_dir: Directory where the agent should work
            prompt: The full prompt including spec and instructions
            model: Model identifier to use
            timeout_sec: Maximum time to allow
            run_dir: Directory to save logs
            
        Returns:
            AgentResult with exit code, output, and timeout status
        """
        pass
    
    def build_prompt(self, spec: str, system_prompt: str, contract: str) -> str:
        """Build the full prompt for the agent."""
        return f"""{system_prompt}

## Contract Requirements

{contract}

## Specification

{spec}

## Instructions

Implement the service according to the specification above. The service must:
1. Listen on the port specified by the PORT environment variable
2. Implement all endpoints in the specification
3. Expose GET /healthz that returns 200 when ready
4. Be startable via ./run.sh

Create all necessary files and a run.sh script that starts the service.
When you are done, the test suite will verify your implementation.
"""
