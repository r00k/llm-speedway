# LLM Speedway Agent Instructions

## Commands

- **Run experiments**: `uv run python -m harness.orchestrate start --task <task> [--agents ...] [--runs N]`
- **Check status**: `uv run python -m harness.orchestrate status`
- **View logs**: `uv run python -m harness.orchestrate logs`
- **Stop experiments**: `uv run python -m harness.orchestrate stop`

## Results

Use the results CLI to query experiment results:

```bash
# Show stats for a task
uv run python -m harness.results_cli stats --task <task>

# List results with filters
uv run python -m harness.results_cli list --task <task> --agent <agent>

# Show errors
uv run python -m harness.results_cli errors

# Show latest result per group
uv run python -m harness.results_cli latest
```

## Testing

```bash
uv run pytest harness/tests/
```
