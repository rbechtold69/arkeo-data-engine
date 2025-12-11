#!/usr/bin/env bash
set -e

echo "Dashboard-core (cache sync + web UI only)"

ARKEOD_HOME=${ARKEOD_HOME:-/root/.arkeo}
ARKEOD_HOME=${ARKEOD_HOME/#\~/$HOME}
ARKEOD_NODE=${ARKEOD_NODE:-tcp://127.0.0.1:26657}
ADMIN_PORT=${ADMIN_PORT:-${ENV_ADMIN_PORT:-8077}}
ADMIN_API_PORT=${ADMIN_API_PORT:-${ENV_ADMIN_API_PORT:-9996}}
CACHE_DIR=${CACHE_DIR:-/app/cache}
CACHE_INIT_ON_START=${CACHE_INIT_ON_START:-1}
CACHE_INIT_TIMEOUT=${CACHE_INIT_TIMEOUT:-120}
CACHE_FETCH_INTERVAL=${CACHE_FETCH_INTERVAL:-300}
BLOCK_HEIGHT_INTERVAL=${BLOCK_HEIGHT_INTERVAL:-60}
BLOCK_TIME_SECONDS=${BLOCK_TIME_SECONDS:-5.79954919}

echo "Using:"
echo "  ARKEOD_HOME          = $ARKEOD_HOME"
echo "  ARKEOD_NODE          = $ARKEOD_NODE"
echo "  ADMIN_PORT           = $ADMIN_PORT"
echo "  ADMIN_API_PORT       = $ADMIN_API_PORT"
echo "  CACHE_DIR            = $CACHE_DIR"
echo "  CACHE_INIT_ON_START  = $CACHE_INIT_ON_START"
echo "  CACHE_INIT_TIMEOUT   = ${CACHE_INIT_TIMEOUT}s"
echo "  CACHE_FETCH_INTERVAL = ${CACHE_FETCH_INTERVAL}s"
echo "  BLOCK_HEIGHT_INTERVAL= ${BLOCK_HEIGHT_INTERVAL}s"
echo "  BLOCK_TIME_SECONDS   = ${BLOCK_TIME_SECONDS}"

# Ensure home directory exists and point ~/.arkeo at ARKEOD_HOME
mkdir -p "$ARKEOD_HOME"
if [ "$ARKEOD_HOME" != "$HOME/.arkeo" ]; then
  ln -sfn "$ARKEOD_HOME" "$HOME/.arkeo"
fi

mkdir -p /app/config
mkdir -p "$CACHE_DIR"
mkdir -p /var/run /var/log/supervisor

INIT_LOG=/var/log/dashboard-init.log
if [ "${CACHE_INIT_ON_START}" != "0" ]; then
  echo "[init] Triggering initial cache sync (timeout ${CACHE_INIT_TIMEOUT}s)..."
  {
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] cache init start (timeout=${CACHE_INIT_TIMEOUT}s)"
  } >> "$INIT_LOG" 2>&1
  (
    if timeout "${CACHE_INIT_TIMEOUT}" python3 /app/cache_fetcher.py --once >> /var/log/dashboard-cache.log 2>&1; then
      echo "[init] Initial cache sync complete." | tee -a "$INIT_LOG"
      echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] cache init success" >> "$INIT_LOG" 2>&1
    else
      echo "[init] Initial cache sync failed or timed out (continuing; supervisor will keep cache_fetcher running)." | tee -a "$INIT_LOG"
      echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] cache init failed" >> "$INIT_LOG" 2>&1
    fi
  ) &
else
  echo "[init] Skipping initial cache sync (CACHE_INIT_ON_START=0)."
  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] cache init skipped" >> "$INIT_LOG" 2>&1
fi

export ENV_ADMIN_PORT="$ADMIN_PORT"
export ENV_ADMIN_API_PORT="$ADMIN_API_PORT"

echo "Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
