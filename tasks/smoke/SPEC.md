# Smoke Test Service

Build a minimal HTTP service with two endpoints.

## Endpoints

### GET /healthz
Returns 200 with JSON body: `{"status": "ok"}`

### GET /echo?message={text}
Returns 200 with JSON body: `{"message": "{text}"}`

If the `message` query parameter is missing, return 400 with: `{"error": "missing message"}`

## Requirements

- Listen on the port specified by the `PORT` environment variable
- Create a `run.sh` script that starts the service
