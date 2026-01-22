"""Run experiments across all agents with the same parameters."""

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Default agent/model pairs
AGENTS = [
    ("amp", "smart"),
    ("claude-code", "claude-opus-4-5"),
    ("codex", "codex-5.2"),
]


def run_experiment(task: str, agent: str, model: str, language: str | None, constraints: list[str] | None) -> tuple[str, bool]:
    """Run a single experiment, return (agent, success)."""
    cmd = [
        sys.executable, "-m", "harness.run_experiment",
        "--task", task,
        "--agent", agent,
        "--model", model,
    ]
    if language:
        cmd.extend(["--language", language])
    for c in constraints or []:
        cmd.extend(["--constraint", c])
    
    print(f"Starting: {agent}/{model}")
    result = subprocess.run(cmd, capture_output=False)
    return agent, result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run experiments across all agents")
    parser.add_argument("--task", required=True, help="Task name")
    parser.add_argument("--language", help="Force a specific language")
    parser.add_argument("--constraint", action="append", dest="constraints",
                        help="Add a constraint (can be repeated)")
    parser.add_argument("--parallel", action="store_true", 
                        help="Run agents in parallel")
    parser.add_argument("--agents", nargs="+", 
                        help="Specific agents to run (default: all)")
    
    args = parser.parse_args()
    
    # Filter agents if specified
    agents_to_run = AGENTS
    if args.agents:
        agents_to_run = [(a, m) for a, m in AGENTS if a in args.agents]
    
    print(f"\n{'='*60}")
    print(f"Running {len(agents_to_run)} agents on task: {args.task}")
    if args.language:
        print(f"Language: {args.language}")
    if args.constraints:
        print(f"Constraints: {', '.join(args.constraints)}")
    print(f"{'='*60}\n")
    
    if args.parallel:
        with ThreadPoolExecutor(max_workers=len(agents_to_run)) as executor:
            futures = {
                executor.submit(run_experiment, args.task, agent, model, args.language, args.constraints): agent
                for agent, model in agents_to_run
            }
            for future in as_completed(futures):
                agent, success = future.result()
                status = "✓" if success else "✗"
                print(f"{status} {agent} completed")
    else:
        for agent, model in agents_to_run:
            run_experiment(args.task, agent, model, args.language, args.constraints)


if __name__ == "__main__":
    main()
