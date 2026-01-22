"""Main experiment runner."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .config import TaskConfig, get_prompt_variant, get_task_wrapper, get_spec
from .workspace import create_run_id, create_workspace, get_run_dir
from .timers import ExperimentTimer
from .service import ServiceManager, get_free_port
from .test_runner import SuiteRunner
from .results import ExperimentResult, save_run_result
from .agents import get_agent


def run_single_experiment(
    task: str,
    agent_name: str,
    model: str,
    prompt_variant: str,
    verbose: bool = False,
) -> ExperimentResult:
    """Run a single experiment and return the result."""
    
    # Load configuration
    task_config = TaskConfig.load(task)
    spec = get_spec(task)
    system_prompt = get_prompt_variant(prompt_variant)
    contract = get_task_wrapper()
    
    # Create workspace
    run_id = create_run_id(task, agent_name, model, prompt_variant)
    workspace_dir = create_workspace(task, run_id)
    run_dir = get_run_dir(run_id)
    
    print(f"\n{'='*60}")
    print(f"Run: {run_id}")
    print(f"Agent: {agent_name} | Model: {model} | Prompt: {prompt_variant}")
    print(f"{'='*60}\n")
    
    # Start timer
    timer = ExperimentTimer()
    timer.start()
    
    # Get agent and build prompt
    agent = get_agent(agent_name)
    full_prompt = agent.build_prompt(spec, system_prompt, contract)
    
    # Run agent
    print("Running agent...")
    agent_result = agent.run(
        workspace_dir=workspace_dir,
        prompt=full_prompt,
        model=model,
        timeout_sec=task_config.timeout_minutes * 60,
        run_dir=run_dir,
    )
    
    if agent_result.timed_out:
        timer.stop()
        result = ExperimentResult(
            run_id=run_id, task=task, agent=agent_name, model=model,
            prompt_variant=prompt_variant, status="timeout",
            duration_sec=timer.elapsed(), error_message="Agent timed out",
        )
        save_run_result(run_id, result)
        print(f"TIMEOUT after {timer.elapsed()}s")
        return result
    
    # Start service on a free port
    port = get_free_port()
    print(f"Starting service on port {port}...")
    service = ServiceManager(
        workspace_dir=workspace_dir,
        port=port,
        healthz_path=task_config.healthz_path,
        healthz_timeout_sec=task_config.healthz_timeout_sec,
    )
    
    try:
        service_ready = service.start(run_dir)
        
        if not service_ready:
            timer.stop()
            result = ExperimentResult(
                run_id=run_id, task=task, agent=agent_name, model=model,
                prompt_variant=prompt_variant, status="error",
                duration_sec=timer.elapsed(), error_message="Service failed to start",
            )
            save_run_result(run_id, result)
            print(f"ERROR: Service failed to start ({timer.elapsed()}s)")
            return result
        
        # Run tests
        print("Confirming model performance by re-running our pristine test suite...")
        test_runner = SuiteRunner(task, service.base_url)
        test_result = test_runner.run(run_dir=run_dir)
        
        # Check if service crashed during tests
        service_crashed = not service.is_running()
        service_exit_code = service.get_exit_code()
        
    finally:
        service.stop()
    
    timer.stop()
    
    # Determine status and error message
    if service_crashed and not test_result.passed:
        status = "error"
        error_message = f"Service crashed during tests (exit code: {service_exit_code})"
        if test_result.error_message:
            error_message += f" - {test_result.error_message}"
    elif test_result.passed:
        status = "pass"
        error_message = None
    else:
        status = "fail"
        error_message = test_result.error_message
    
    result = ExperimentResult(
        run_id=run_id, task=task, agent=agent_name, model=model,
        prompt_variant=prompt_variant, status=status, duration_sec=timer.elapsed(),
        error_message=error_message,
    )
    save_run_result(run_id, result)
    
    print(f"\n{'='*60}")
    print(f"{status.upper()} — {timer.elapsed():.2f}s")
    if test_result.error_message:
        print(f"\n{test_result.error_message}")
    elif test_result.failed_tests:
        print(f"\nFailed tests:")
        for test_name in test_result.failed_tests:
            print(f"  • {test_name}")
    print(f"{'='*60}\n")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Run LLM Speedway experiments")
    parser.add_argument("--task", required=True, help="Task name (e.g., issue-tracker)")
    parser.add_argument("--agent", required=True, help="Agent to test (codex, claude-code)")
    parser.add_argument("--model", required=True, help="Model to use")
    parser.add_argument("--prompt-variant", default="default", help="Prompt variant")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    run_single_experiment(
        task=args.task,
        agent_name=args.agent,
        model=args.model,
        prompt_variant=args.prompt_variant,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
