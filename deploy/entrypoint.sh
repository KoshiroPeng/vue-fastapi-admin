#!/bin/sh
set -e

# Nginx records sanitized access logs. Uvicorn access logs are disabled because
# the legacy mini-program contract carries its password in the query string.
exec uvicorn app:app --host 0.0.0.0 --port 9999 --workers "${UVICORN_WORKERS:-1}" --no-access-log
