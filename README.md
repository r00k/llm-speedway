# LLM Speedway

Benchmark harness for timing agentic coding tools. Measures end-to-end time for AI agents to implement a service from spec and pass tests.

## Usage

```bash
uv sync

# Test Amp (smart mode)
uv run python -m harness.run_experiment \
  --task conference-scheduler \
  --agent amp \
  --model smart

# Test Claude Code
uv run python -m harness.run_experiment \
  --task conference-scheduler \
  --agent claude-code \
  --model claude-sonnet-4

# Test Codex CLI
uv run python -m harness.run_experiment \
  --task issue-tracker \
  --agent codex \
  --model o3
```

## How It Works

1. Agent receives a spec + test contract
2. Agent implements the service (any language)
3. Harness starts the service via `./run.sh`
4. Black-box HTTP tests verify correctness
5. End-to-end time recorded to `results/results.jsonl`

## Agents

| Agent | CLI | Model Examples |
|-------|-----|----------------|
| `amp` | `amp -x` | `smart`, `free`, `rush` |
| `claude-code` | `claude` | `claude-sonnet-4`, `claude-opus-4` |
| `codex` | `codex` | `o3`, `o4-mini` |

## Tasks

| Task | Description |
|------|-------------|
| `conference-scheduler` | Constraint satisfaction REST API (~10 hard constraints) |
| `issue-tracker` | CRUD REST API with labels, comments, projects |
| `smoke` | Minimal health-check endpoint (for testing harness) |

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
{"agent": "amp", "model": "smart", "task": "conference-scheduler", "status": "pass", "duration_sec": 287.3}
{"agent": "claude-code", "model": "claude-sonnet-4", "task": "issue-tracker", "status": "pass", "duration_sec": 342.5}
```

## Structure

```
harness/                    # Runner + agent adapters
prompts/                    # System prompt variants  
tasks/                      # Benchmark specs + tests
  conference-scheduler/     # Constraint satisfaction problem
  issue-tracker/            # CRUD REST API
  smoke/                    # Minimal test task
runs/                       # Execution logs
results/                    # Results JSONL
```
