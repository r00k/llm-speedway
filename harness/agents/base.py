"""Base class for agent adapters."""

from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import subprocess
import sys
import os
import signal
import threading


@dataclass
class AgentResult:
    """Result of running an agent."""
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


def run_with_streaming(
    cmd: list[str],
    cwd: Path,
    env: dict,
    timeout_sec: int,
    run_dir: Optional[Path] = None,
) -> AgentResult:
    """
    Run a command with real-time streaming to stdout and log files.
    
    Uses a PTY to ensure CLIs don't buffer their output.
    
    Output is streamed to:
    - stdout (so user can see progress)
    - agent.stdout.log (for persistence)
    """
    import pty
    import select
    
    output_log = []
    timed_out = False
    exit_code = 0
    
    # Open log file if run_dir provided
    log_file = None
    if run_dir:
        run_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(run_dir / "agent.stdout.log", "w")
        # Also create empty stderr log for consistency
        (run_dir / "agent.stderr.log").write_text("")
    
    try:
        # Create a pseudo-terminal so the CLI thinks it's interactive
        master_fd, slave_fd = pty.openpty()
        
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=slave_fd,
            stderr=slave_fd,
            stdin=slave_fd,
            text=False,
        )
        
        os.close(slave_fd)
        
        import time
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout_sec:
                proc.kill()
                timed_out = True
                break
            
            # Check if process is done
            poll_result = proc.poll()
            
            # Read available output
            ready, _, _ = select.select([master_fd], [], [], 0.1)
            if ready:
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        text = data.decode('utf-8', errors='replace')
                        output_log.append(text)
                        sys.stdout.write(text)
                        sys.stdout.flush()
                        if log_file:
                            log_file.write(text)
                            log_file.flush()
                except OSError:
                    pass
            
            if poll_result is not None:
                # Process finished, drain remaining output
                while True:
                    ready, _, _ = select.select([master_fd], [], [], 0.1)
                    if not ready:
                        break
                    try:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        text = data.decode('utf-8', errors='replace')
                        output_log.append(text)
                        sys.stdout.write(text)
                        sys.stdout.flush()
                        if log_file:
                            log_file.write(text)
                            log_file.flush()
                    except OSError:
                        break
                exit_code = poll_result
                break
        
        os.close(master_fd)
        
    except FileNotFoundError:
        error_msg = f"Command not found: {cmd[0]}\n"
        output_log.append(error_msg)
        sys.stderr.write(error_msg)
        if log_file:
            log_file.write(error_msg)
        exit_code = 127
    
    finally:
        if log_file:
            log_file.close()
    
    return AgentResult(
        exit_code=exit_code,
        stdout="".join(output_log),
        stderr="",
        timed_out=timed_out,
    )


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
