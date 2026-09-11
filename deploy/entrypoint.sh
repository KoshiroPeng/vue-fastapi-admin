#!/bin/sh
set -e

exec uvicorn app:app --host 0.0.0.0 --port 9999 --workers "${UVICORN_WORKERS:-1}"
