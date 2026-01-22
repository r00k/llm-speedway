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
  --model claude-opus-4-5

# Test Codex CLI
uv run python -m harness.run_experiment \
  --task issue-tracker \
  --agent codex \
  --model codex-5.2
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
| `claude-code` | `claude` | `claude-opus-4-5`, `claude-sonnet-4-5` |
| `codex` | `codex` | `codex-5.2`, `codex-5.2-mini` |

## Tasks

| Task | Description |
|------|-------------|
| `conference-scheduler` | Constraint satisfaction REST API (~10 hard constraints) |
| `issue-tracker` | CRUD REST API with labels, comments, projects |
| `smoke` | Minimal health-check endpoint (for testing harness) |

## Language Constraint

Force a specific programming language:

```bash
--language Go
--language Rust
--language Python
```

## Custom Constraints

Add arbitrary constraints (can be repeated):

```bash
--constraint "use only 5 files"
--constraint "all functions must be shorter than 10 lines"
--constraint "do not use any external dependencies"
```

Example with both:

```bash
uv run python -m harness.run_experiment \
  --task conference-scheduler \
  --agent amp \
  --model smart \
  --language Go \
  --constraint "use only 5 files"
```

## Results

```json
{"agent": "amp", "model": "smart", "task": "conference-scheduler", "status": "pass", "duration_sec": 287.3}
{"agent": "claude-code", "model": "claude-opus-4-5", "task": "issue-tracker", "status": "pass", "duration_sec": 342.5}
```

## Structure

```
harness/                    # Runner + agent adapters
prompts/                    # System prompts  
tasks/                      # Benchmark specs + tests
  conference-scheduler/     # Constraint satisfaction problem
  issue-tracker/            # CRUD REST API
  smoke/                    # Minimal test task
runs/                       # Execution logs
results/                    # Results JSONL
```
