# HTTP Service Contract (Self-Testing)

Your implementation MUST follow this contract.

## Your Task

1. Read the specification carefully
2. Write a comprehensive test suite in `tests/` that covers the spec
3. Implement the service to pass your tests
4. Verify with `./run.sh` and `pytest tests/`

## Test Requirements

Your test suite must:
- Use pytest with httpx or requests for HTTP calls
- Cover all endpoints and behaviors in the spec
- Test happy paths, edge cases, and error handling
- Name test files `test_*.py`

Create a `tests/conftest.py` with:
```python
import pytest
import os

@pytest.fixture
def base_url():
    return os.environ.get("SERVICE_URL", "http://localhost:8080")
```

## Required Files

### run.sh
Create a `run.sh` script that starts the service. Requirements:
- Must be executable (`chmod +x run.sh`)
- Must block (not exit until killed)
- Must read the `PORT` environment variable for the port to listen on
- May use `DATA_DIR` environment variable for data storage location
- Must log to stdout/stderr

Example structure:
```bash
#!/bin/bash
# Install dependencies if needed, then start the service
# The service must listen on $PORT
```

## Required Endpoints

### Health Check
```
GET /healthz
```
- Returns HTTP 200 when the service is ready to accept requests
- Returns HTTP 503 if not ready
- Used by the test harness to determine when to start testing

## HTTP Conventions

- All endpoints should return JSON unless otherwise specified
- Use appropriate HTTP status codes (200, 201, 400, 404, 409, 500, etc.)
- Include `Content-Type: application/json` header on JSON responses
- Parse JSON request bodies for POST/PUT/PATCH requests

## Error Response Format

For errors, return JSON with at least an `error` field:
```json
{
  "error": "Description of what went wrong"
}
```

## Data Persistence

- Data must persist for the lifetime of the service process
- You may use SQLite, a JSON file, or in-memory storage
- If using files, use the `DATA_DIR` environment variable if set

## Important

Make sure ALL tests pass before you stop working.
