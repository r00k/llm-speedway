"""Codex CLI agent adapter."""

import subprocess
import os
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
        full_prompt = "Read .speedway_prompt.md and implement the service exactly as specified. Create all necessary files including run.sh."
        
        # Use codex exec for non-interactive mode
        # --dangerously-bypass-approvals-and-sandbox (--yolo): skip all permission prompts
        # --skip-git-repo-check: workspace may not be a git repo
        cmd = [
            "codex", "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            full_prompt,
        ]
        
        env = os.environ.copy()
        
        stdout_log = ""
        stderr_log = ""
        timed_out = False
        
        try:
            result = subprocess.run(
                cmd,
                cwd=workspace_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            stdout_log = result.stdout
            stderr_log = result.stderr
            exit_code = result.returncode
            
        except subprocess.TimeoutExpired as e:
            stdout_log = e.stdout.decode() if e.stdout else ""
            stderr_log = e.stderr.decode() if e.stderr else ""
            exit_code = -1
            timed_out = True
        
        except FileNotFoundError:
            stderr_log = "codex CLI not found. Install with: npm install -g @openai/codex"
            exit_code = 127
        
        # Save logs if run_dir provided
        if run_dir:
            (run_dir / "agent.stdout.log").write_text(stdout_log)
            (run_dir / "agent.stderr.log").write_text(stderr_log)
        
        return AgentResult(
            exit_code=exit_code,
            stdout=stdout_log,
            stderr=stderr_log,
            timed_out=timed_out,
        )
