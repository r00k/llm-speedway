# LLM Speedway

Benchmark harness for timing agentic coding tools. Measures end-to-end time for AI agents to implement a service from spec and pass tests.

## Usage

```bash
uv sync

# Test Codex 5.2
uv run python -m harness.run_experiment \
  --task issue-tracker \
  --agent codex \
  --model codex-5.2

# Test Claude Code (Opus 4.5)
uv run python -m harness.run_experiment \
  --task issue-tracker \
  --agent claude-code \
  --model opus-4.5
```

## How It Works

1. Agent receives a spec + test contract
2. Agent implements the service (any language)
3. Harness starts the service via `./run.sh`
4. Black-box HTTP tests verify correctness
5. End-to-end time recorded to `results/results.jsonl`

## Prompt Variants

Run experiments with different constraints:

```bash
--prompt-variant default         # No constraints
--prompt-variant short-functions # Max 10 lines per function
--prompt-variant force-go        # Must use Go
--prompt-variant force-haskell   # Must use Haskell
```

## Results

```json
{"agent": "codex", "model": "codex-5.2", "status": "pass", "duration_sec": 342.5}
{"agent": "claude-code", "model": "opus-4.5", "status": "pass", "duration_sec": 287.3}
```

## Structure

```
harness/          # Runner + agent adapters
prompts/          # System prompt variants  
tasks/            # Benchmark specs + tests
  issue-tracker/  # ~2000 LOC REST API task
runs/             # Execution logs
```
