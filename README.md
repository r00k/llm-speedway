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

# Run all 3 agents on the same task
uv run python -m harness.run_all --task conference-scheduler

# Run all agents in parallel with language constraint
uv run python -m harness.run_all --task conference-scheduler --language Go --parallel
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
| `language-rewrite` | Rewrite a Python rate limiter service into another language |
| `smoke` | Minimal health-check endpoint (for testing harness) |

See [tasks/README.md](tasks/README.md) for how to create new tasks.

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

## Self-Testing Mode

Require models to write their own tests instead of providing a test suite:

```bash
uv run python -m harness.run_experiment \
  --task conference-scheduler \
  --agent amp \
  --model smart \
  --write-own-tests

# Or with run_all
uv run python -m harness.run_all --task smoke --write-own-tests --parallel
```

In this mode:
- Models receive only the spec (no `_tests/` folder)
- Models must write their own test suite in `tests/`
- Harness validates with hidden tests at the end

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
