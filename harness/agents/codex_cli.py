"""Codex CLI agent adapter."""

import os
import subprocess
from pathlib import Path
from typing import Optional

from .base import AgentRunner, AgentResult


class CodexCLIRunner(AgentRunner):
    """Adapter for OpenAI Codex CLI."""
    
    name = "codex"
    
    def run(
        self,
        workspace_dir: Path,
        prompt: str,
        model: str = "codex-5.2",
        timeout_sec: int = 3600,
        run_dir: Optional[Path] = None,
    ) -> AgentResult:
        """Run Codex CLI with the given prompt using codex exec."""
        
        # Write prompt to a file for reference
        prompt_file = workspace_dir / ".speedway_prompt.md"
        prompt_file.write_text(prompt)
        
        # Build the full prompt - tell it to read the file
        full_prompt = "Read .speedway_prompt.md and implement the service exactly as specified. Create all necessary files including run.sh. Run the test suite with ./run_tests.sh and fix any failures. Do not stop until ALL tests pass."
        
        # Use codex exec for non-interactive mode
        cmd = [
            "codex", "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            full_prompt,
        ]
        
        env = os.environ.copy()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=workspace_dir,
                env=env,
                timeout=timeout_sec,
                capture_output=True,
                text=True,
            )
            return AgentResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            return AgentResult(exit_code=-1, stdout="", stderr="", timed_out=True)
        except FileNotFoundError:
            return AgentResult(exit_code=127, stdout="", stderr="codex not found")
