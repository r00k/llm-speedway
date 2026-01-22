"""Amp agent adapter."""

import os
from pathlib import Path
from typing import Optional

from .base import AgentRunner, AgentResult, run_with_streaming


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
            "--mode", model,
        ]
        
        env = os.environ.copy()
        
        return run_with_streaming(
            cmd=cmd,
            cwd=workspace_dir,
            env=env,
            timeout_sec=timeout_sec,
            run_dir=run_dir,
        )
