"""Claude Code agent adapter."""

import os
import subprocess
from pathlib import Path
from typing import Optional

from .base import AgentRunner, AgentResult


class ClaudeCodeRunner(AgentRunner):
    """Adapter for Claude Code CLI."""
    
    name = "claude-code"
    
    def run(
        self,
        workspace_dir: Path,
        prompt: str,
        model: str = "opus",
        timeout_sec: int = 3600,
        run_dir: Optional[Path] = None,
    ) -> AgentResult:
        """Run Claude Code with the given prompt using claude -p."""
        
        # Write prompt to a file for reference
        prompt_file = workspace_dir / ".speedway_prompt.md"
        prompt_file.write_text(prompt)
        
        # Build the full prompt
        full_prompt = "Read .speedway_prompt.md and implement the service exactly as specified. Create all necessary files including run.sh."
        
        cmd = [
            "claude",
            "-p", full_prompt,
            "--dangerously-skip-permissions",
            "--model", model,
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
            return AgentResult(exit_code=127, stdout="", stderr="claude not found")
