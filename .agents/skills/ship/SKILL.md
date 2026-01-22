---
name: ship
description: Commits, tests, and pushes code changes. Use when asked to "ship", "ship it", or push changes to remote.
---

# Ship

Fast workflow for committing, testing, and pushing code.

Goal: run this skill quickly! 

## Workflow

Execute these steps, parallelizing where possible:

### Step 1: Commit and Test (parallel)

Run these simultaneously:

1. **Commit all changes** with a focused commit message that emphasizes why the changes are being made rather than what was done.

2. **Run tests** to check for failures:
   - Check AGENTS.md first for the test command
   - Otherwise look in `package.json`, `pyproject.toml`, `Makefile`, or similar
   - Common commands: `pytest`, `npm test`, `make test`, `go test ./...`

### Step 2: Handle Results

**If tests pass:**
- Push immediately: `git push`
- Check if documentation needs updates (README, API docs, etc.)
- Update docs in the background if the changes warrant it (commit and push this too)

**If tests fail:**
- Analyze failures and fix the code
- Amend the commit: `git add -A && git commit --amend --no-edit`
- Re-run tests
- Repeat until tests pass (max 3 attempts), then push
- If still failing after 3 attempts, stop and report the issue to the user

### Step 3: Documentation (parallel with push)

While pushing, evaluate if documentation updates are needed:
- New features → update README or relevant docs
- Changed APIs → update API documentation
- Changed CLI flags → update usage docs

Only update docs if there's genuine value; don't make trivial changes.

## Speed Priority

- Always parallelize independent operations
- Don't wait for confirmation between steps
- Parallelize doc updates with push when both are needed
