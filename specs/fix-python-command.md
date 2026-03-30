# Specification: Fix Python Command in Local MLOps Pipeline

The local MLOps pipeline script `backend/scripts/local_mlops_pipeline.sh` fails when running inside the `mlops-pipeline` container because it calls `python` instead of `python3`, which is the correct command available in the `Dockerfile.portable` environment.

## Context
- **Image**: `Dockerfile.portable` (Node Bookworm backend with Python 3.11).
- **Service**: `mlops-pipeline` in `docker-compose.dev.yml`.
- **Command**: `bash -lc ./scripts/local_mlops_pipeline.sh`.
- **Error**: `python: command not found` (Exit code 127).

## Requirements
- Update `backend/scripts/local_mlops_pipeline.sh` to use `python3` for all orchestrator CLI calls.
- Ensure consistency with other backend services (e.g., `backend-api` and `ml-worker`) which already use `python3`.

## Proposed Change
Modify `backend/scripts/local_mlops_pipeline.sh`:
- Change `python scripts/orchestrator_cli.py cleanup` to `python3 scripts/orchestrator_cli.py cleanup`.
- Change `python scripts/orchestrator_cli.py train ...` to `python3 scripts/orchestrator_cli.py train ...`.
- Change `python scripts/orchestrator_cli.py predict ...` to `python3 scripts/orchestrator_cli.py predict ...`.
- Change `python scripts/orchestrator_cli.py top-picks ...` to `python3 scripts/orchestrator_cli.py top-picks ...`.

## Verification
- Re-run `docker compose -f docker-compose.dev.yml --profile mlops run --rm mlops-pipeline`.
- Verify logs show the pipeline starting and completing without "command not found" errors.
