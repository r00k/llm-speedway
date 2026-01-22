# HTTP Service Contract

Your implementation MUST follow this contract.

## Development Workflow

You have access to the test suite in `_tests/`. Use it to verify your implementation as you build:

1. Start your service: `PORT=8080 ./run.sh &`
2. Run tests: `./run_tests.sh`
3. Fix failures and repeat

You can run specific tests with `./run_tests.sh -k "test_name"` or stop on first failure with `./run_tests.sh -x`.

**Tip**: Use a fresh data directory for each test run to avoid state pollution:
```bash
DATA_DIR=$(mktemp -d) PORT=8080 ./run.sh &
./run_tests.sh
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
