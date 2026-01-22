"""Experiment orchestrator using tmux for long-running benchmarks."""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from itertools import product

from .config import RUNS_DIR, RESULTS_DIR

MAX_CONCURRENT = 6  # Max parallel tmux sessions (reduced to avoid API rate limiting)


def generate_experiment_id(task: str, agent: str, model: str, language: str | None, constraints: list[str] | None) -> str:
    """Generate a unique experiment ID with hash suffix for collision resistance."""
    import hashlib
    import uuid
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    # Sanitize for tmux session names (no periods or special chars)
    safe_model = model.replace("-", "").replace(".", "_")[:12]
    safe_agent = agent.replace("-", "")[:8]
    safe_task = task[:12]
    
    # Build readable prefix
    parts = [timestamp, safe_task, safe_agent, safe_model]
    if language:
        parts.append(language.lower()[:4])
    
    # Hash all params + uuid for guaranteed uniqueness
    hash_input = f"{task}:{agent}:{model}:{language}:{constraints}:{uuid.uuid4()}"
    unique_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
    parts.append(unique_hash)
    
    return "_".join(parts)[:80]


def get_active_sessions() -> list[str]:
    """Get list of active tmux sessions starting with 'bench_'."""
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return []
    return [s for s in result.stdout.strip().split("\n") if s.startswith("bench_")]


def start_experiment(
    task: str,
    agent: str,
    model: str,
    language: str | None = None,
    constraints: list[str] | None = None,
) -> str | None:
    """Start a single experiment in a tmux session. Returns session name or None if at capacity."""
    active = get_active_sessions()
    if len(active) >= MAX_CONCURRENT:
        return None
    
    exp_id = generate_experiment_id(task, agent, model, language, constraints)
    session_name = f"bench_{exp_id}"
    
    # Build command with proper quoting
    import shlex
    cmd_parts = [
        "uv", "run", "python", "-m", "harness.run_experiment",
        "--task", task,
        "--agent", agent,
        "--model", model,
    ]
    if language:
        cmd_parts.extend(["--language", language])
    for c in constraints or []:
        cmd_parts.extend(["--constraint", c])
    
    cmd = shlex.join(cmd_parts)
    
    # Create log directory
    log_dir = RUNS_DIR / f"orchestrated_{exp_id}"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "orchestrator.log"
    meta_file = log_dir / "meta.json"
    
    # Write metadata
    meta = {
        "exp_id": exp_id,
        "session": session_name,
        "task": task,
        "agent": agent,
        "model": model,
        "language": language,
        "constraints": constraints,
        "command": cmd,
        "started_at": datetime.utcnow().isoformat(),
        "log_file": str(log_file),
    }
    meta_file.write_text(json.dumps(meta, indent=2))
    
    # Start tmux session with proper error capture
    tmux_cmd = f'''
set -uo pipefail
exec >"{log_file}" 2>&1
echo "=== START $(date) ==="

# Ensure toolchains are in PATH and unbuffered Python output
export PATH="$HOME/.local/bin:/opt/homebrew/opt/openjdk/bin:/opt/homebrew/opt/ruby/bin:/opt/homebrew/bin:$PATH"
export JAVA_HOME="/opt/homebrew/opt/openjdk"
export PYTHONUNBUFFERED=1

cd /Users/ben/code/llm-speedway

# Trap signals for debugging
trap 'echo "=== GOT SIGTERM at $(date) ===" >> "{log_file}"' TERM
trap 'echo "=== GOT SIGHUP at $(date) ===" >> "{log_file}"' HUP
trap 'echo "=== GOT SIGINT at $(date) ===" >> "{log_file}"' INT
trap 'rc=$?; echo "=== EXIT rc=$rc at $(date) ==="; echo $rc > "{log_dir}/exit_code.txt"; date > "{log_dir}/done.txt"' EXIT

echo "=== RUNNING: {cmd} ==="
{cmd}
rc=$?
echo "=== CMD FINISHED rc=$rc ==="
exit $rc
'''
    
    # Small stagger to avoid burst resource contention
    import time, random
    time.sleep(0.1 + random.random() * 0.2)
    
    result = subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, "bash", "-lc", tmux_cmd],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        (log_dir / "tmux_error.txt").write_text(f"stdout: {result.stdout}\nstderr: {result.stderr}")
        return None
    
    print(f"Started: {session_name}")
    return session_name


def start_matrix(
    tasks: list[str],
    agents: list[tuple[str, str]],  # (agent, model) pairs
    languages: list[str | None],
    constraints_sets: list[list[str] | None],
) -> int:
    """Start a matrix of experiments. Returns count started."""
    started = 0
    skipped = 0
    
    for task, (agent, model), language, constraints in product(tasks, agents, languages, constraints_sets):
        session = start_experiment(task, agent, model, language, constraints)
        if session:
            started += 1
        else:
            skipped += 1
            print(f"Skipped (at capacity): {task}/{agent}/{language}")
    
    print(f"\nStarted {started} experiments, skipped {skipped} (capacity: {MAX_CONCURRENT})")
    return started


def status():
    """Show status of all orchestrated experiments."""
    active = get_active_sessions()
    
    # Find all orchestrated runs
    runs = sorted(RUNS_DIR.glob("orchestrated_*"))
    
    running = []
    completed = []
    
    for run_dir in runs:
        meta_file = run_dir / "meta.json"
        done_file = run_dir / "done.txt"
        exit_file = run_dir / "exit_code.txt"
        
        if not meta_file.exists():
            continue
        
        meta = json.loads(meta_file.read_text())
        session = meta.get("session", "")
        
        info = {
            "exp_id": meta.get("exp_id"),
            "task": meta.get("task"),
            "agent": meta.get("agent"),
            "model": meta.get("model"),
            "language": meta.get("language") or "any",
            "started": meta.get("started_at", "")[:19],
        }
        
        if done_file.exists():
            exit_code = exit_file.read_text().strip() if exit_file.exists() else "?"
            info["status"] = "pass" if exit_code == "0" else f"exit:{exit_code}"
            completed.append(info)
        elif session in active:
            info["status"] = "running"
            running.append(info)
        else:
            info["status"] = "unknown"
            completed.append(info)
    
    print(f"\n=== Running ({len(running)}/{MAX_CONCURRENT} slots) ===")
    for r in running:
        print(f"  {r['agent']}/{r['model']} on {r['task']} ({r['language']}) - started {r['started']}")
    
    print(f"\n=== Completed ({len(completed)}) ===")
    for c in completed:
        print(f"  {c['agent']}/{c['model']} on {c['task']} ({c['language']}) - {c['status']}")
    
    return {"running": running, "completed": completed}


def tail_logs(n: int = 20):
    """Show recent log lines from running experiments."""
    active = get_active_sessions()
    
    for run_dir in sorted(RUNS_DIR.glob("orchestrated_*")):
        meta_file = run_dir / "meta.json"
        log_file = run_dir / "orchestrator.log"
        
        if not meta_file.exists() or not log_file.exists():
            continue
        
        meta = json.loads(meta_file.read_text())
        if meta.get("session") not in active:
            continue
        
        print(f"\n=== {meta.get('agent')}/{meta.get('task')} ===")
        result = subprocess.run(["tail", f"-{n}", str(log_file)], capture_output=True, text=True)
        print(result.stdout)


def stop_all():
    """Stop all benchmark tmux sessions."""
    active = get_active_sessions()
    for session in active:
        subprocess.run(["tmux", "kill-session", "-t", session])
        print(f"Stopped: {session}")
    print(f"Stopped {len(active)} sessions")


def main():
    parser = argparse.ArgumentParser(description="Orchestrate LLM benchmark experiments")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # start command
    start_p = subparsers.add_parser("start", help="Start experiments")
    start_p.add_argument("--task", required=True, help="Task name")
    start_p.add_argument("--agents", nargs="+", default=["amp", "claude-code", "codex"],
                         help="Agents to test")
    start_p.add_argument("--languages", nargs="+", default=[None],
                         help="Languages to test (use 'any' for no constraint)")
    start_p.add_argument("--constraint", action="append", dest="constraints",
                         help="Add a constraint")
    
    # matrix command
    matrix_p = subparsers.add_parser("matrix", help="Start a matrix of experiments")
    matrix_p.add_argument("--tasks", nargs="+", required=True)
    matrix_p.add_argument("--languages", nargs="+", default=["any"])
    
    # status command
    subparsers.add_parser("status", help="Show experiment status")
    
    # logs command
    logs_p = subparsers.add_parser("logs", help="Tail running experiment logs")
    logs_p.add_argument("-n", type=int, default=20, help="Number of lines")
    
    # stop command
    subparsers.add_parser("stop", help="Stop all experiments")
    
    args = parser.parse_args()
    
    if args.command == "start":
        agents = [
            ("amp", "smart"),
            ("claude-code", "claude-opus-4-5"),
            ("codex", "codex-5.2"),
        ]
        agents = [(a, m) for a, m in agents if a in args.agents]
        languages = [None if l == "any" else l for l in args.languages]
        constraints_sets = [args.constraints] if args.constraints else [None]
        
        start_matrix([args.task], agents, languages, constraints_sets)
    
    elif args.command == "matrix":
        agents = [
            ("amp", "smart"),
            ("claude-code", "claude-opus-4-5"),
            ("codex", "codex-5.2"),
        ]
        languages = [None if l == "any" else l for l in args.languages]
        start_matrix(args.tasks, agents, languages, [None])
    
    elif args.command == "status":
        status()
    
    elif args.command == "logs":
        tail_logs(args.n)
    
    elif args.command == "stop":
        stop_all()


if __name__ == "__main__":
    main()
