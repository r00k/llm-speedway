"""Amp agent adapter."""

import subprocess
import os
from pathlib import Path
from typing import Optional

from .base import AgentRunner, AgentResult


class AmpRunner(AgentRunner):
    """Adapter for Amp CLI."""
    
    name = "amp"
    
    def run(
        self,
        workspace_dir: Path,
        prompt: str,
        model: str = "smart",
        timeout_sec: int = 3600,
        run_dir: Optional[Path] = None,
    ) -> AgentResult:
        """Run Amp with the given prompt using amp -x."""
        
        # Write prompt to a file for reference
        prompt_file = workspace_dir / ".speedway_prompt.md"
        prompt_file.write_text(prompt)
        
        # Build the full prompt
        full_prompt = "Read .speedway_prompt.md and implement the service exactly as specified. Create all necessary files including run.sh."
        
        # Use amp -x for execute mode
        # --dangerously-allow-all: skip all permission prompts
        # --mode: specify mode (free, rush, smart)
        cmd = [
            "amp",
            "-x", full_prompt,
            "--dangerously-allow-all",
        ]
        
        # Add mode
        cmd.extend(["--mode", model])
        
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
            stderr_log = "amp CLI not found. Install from https://ampcode.com"
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
