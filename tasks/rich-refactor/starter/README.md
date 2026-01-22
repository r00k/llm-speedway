# Rich Refactoring Task

This task requires you to refactor an existing codebase rather than build something from scratch.

## Setup

The harness will clone the `rich` library repository and set up the environment for you.

## Your Task

Read `SPEC.md` carefully and perform the refactoring as specified.

## Key Points

1. This is a **behavior-preserving refactoring** - all existing tests must pass
2. You're extracting methods from `Text` class into a new module
3. The `Text` class methods become thin wrappers
4. Avoid import cycles using `TYPE_CHECKING`

## Testing Your Work

```bash
# Run the structural verification
python tests/verify_structure.py

# Run the behavioral tests
pytest tests/test_text.py -v

# Quick smoke test
python -c "from rich.text import Text; t = Text('hello'); t.truncate(3); print(t)"
```
