"""Claude Code agent adapter."""

import os
from pathlib import Path
from typing import Optional

from .base import AgentRunner, AgentResult, run_with_streaming


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
        
        # Use claude -p for non-interactive mode
        # --dangerously-skip-permissions: skip all permission prompts
        # --model: specify model
        cmd = [
            "claude",
            "-p", full_prompt,
            "--dangerously-skip-permissions",
            "--model", model,
        ]
        
        env = os.environ.copy()
        
        return run_with_streaming(
            cmd=cmd,
            cwd=workspace_dir,
            env=env,
            timeout_sec=timeout_sec,
            run_dir=run_dir,
        )
