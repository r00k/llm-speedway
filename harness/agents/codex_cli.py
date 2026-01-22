"""Codex CLI agent adapter."""

import os
from pathlib import Path
from typing import Optional

from .base import AgentRunner, AgentResult, run_with_streaming


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
        
        return run_with_streaming(
            cmd=cmd,
            cwd=workspace_dir,
            env=env,
            timeout_sec=timeout_sec,
            run_dir=run_dir,
        )
