# Issue Tracker Implementation

Implement the issue tracker service according to SPEC.md.

## Requirements

1. Create your implementation files
2. Update `run.sh` to start your service
3. Your service must listen on the port specified by `$PORT`
4. Implement `GET /healthz` returning 200 when ready

## Testing

The test harness will:
1. Run `./run.sh` to start your service
2. Wait for `GET /healthz` to return 200
3. Run the test suite against your service
