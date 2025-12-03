#!/usr/bin/env bash
set -e

ADMIN_PORT=${ENV_ADMIN_PORT:-${ADMIN_PORT:-8078}}

echo "Starting Arkeo testing-core static page on port ${ADMIN_PORT} (no sentinel, no APIs)..."
mkdir -p /app/config

exec python3 /app/server.py
