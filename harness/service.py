"""Service lifecycle management."""

import subprocess
import time
import signal
import os
import socket
from pathlib import Path
from typing import Optional
import httpx


def get_free_port() -> int:
    """Find and return a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


class ServiceManager:
    """Manages the lifecycle of a service under test."""
    
    def __init__(
        self,
        workspace_dir: Path,
        port: int,
        healthz_path: str = "/healthz",
        healthz_timeout_sec: int = 120,
    ):
        self.workspace_dir = workspace_dir
        self.port = port
        self.healthz_path = healthz_path
        self.healthz_timeout_sec = healthz_timeout_sec
        self._process: Optional[subprocess.Popen] = None
        self._stdout_file: Optional[object] = None
        self._stderr_file: Optional[object] = None
    
    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"
    
    def start(self, run_dir: Path) -> bool:
        """Start the service. Returns True if started successfully."""
        run_script = self.workspace_dir / "run.sh"
        
        if not run_script.exists():
            raise FileNotFoundError(f"run.sh not found in {self.workspace_dir}")
        
        # Make executable
        os.chmod(run_script, 0o755)
        
        # Open log files
        self._stdout_file = open(run_dir / "service.stdout.log", "w")
        self._stderr_file = open(run_dir / "service.stderr.log", "w")
        
        # Start service
        env = os.environ.copy()
        env["PORT"] = str(self.port)
        data_dir = self.workspace_dir / "data"
        data_dir.mkdir(exist_ok=True)
        env["DATA_DIR"] = str(data_dir)
        
        # Disable Flask/Werkzeug reloader and debug mode to prevent
        # restarts when test framework creates cache files
        env["FLASK_DEBUG"] = "0"
        env["FLASK_ENV"] = "production"
        env["WERKZEUG_RUN_MAIN"] = "true"
        
        self._process = subprocess.Popen(
            ["bash", "run.sh"],
            cwd=self.workspace_dir,
            env=env,
            stdout=self._stdout_file,
            stderr=self._stderr_file,
            start_new_session=True,  # Isolate from parent signals
        )
        
        return self._wait_for_ready()
    
    def _wait_for_ready(self) -> bool:
        """Wait for the service to become ready."""
        url = f"{self.base_url}{self.healthz_path}"
        deadline = time.monotonic() + self.healthz_timeout_sec
        
        while time.monotonic() < deadline:
            # Check if process died
            if self._process and self._process.poll() is not None:
                return False
            
            try:
                resp = httpx.get(url, timeout=2.0)
                if resp.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            
            time.sleep(0.5)
        
        return False
    
    def stop(self):
        """Stop the service."""
        if self._process:
            # Try graceful shutdown first - send to process group
            try:
                os.killpg(self._process.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill the process group
                try:
                    os.killpg(self._process.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                self._process.wait()
            self._process = None
        
        if self._stdout_file:
            self._stdout_file.close()
            self._stdout_file = None
        
        if self._stderr_file:
            self._stderr_file.close()
            self._stderr_file = None
    
    def is_running(self) -> bool:
        """Check if the service is running."""
        if self._process is None:
            return False
        return self._process.poll() is None
    
    def get_exit_code(self) -> Optional[int]:
        """Get the exit code if the process has terminated."""
        if self._process is None:
            return None
        return self._process.poll()
