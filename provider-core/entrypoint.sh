#!/usr/bin/env bash
set -e

CHAIN_HOME=${CHAIN_HOME:-/root/.arkeod}
CHAIN_ID=${CHAIN_ID:-arkeochain-1}

# Initialize chain on first run
if [ ! -d "$CHAIN_HOME/config" ]; then
  echo "Initializing provider node..."
  arkeod init "provider-node" --chain-id "$CHAIN_ID" --home "$CHAIN_HOME"

  # If you have prebuilt config/genesis in /app/config, copy them over:
  if [ -f /app/config/genesis.json ]; then
      cp /app/config/genesis.json "$CHAIN_HOME/config/genesis.json"
  fi
  if [ -f /app/config/config.toml ]; then
      cp /app/config/config.toml "$CHAIN_HOME/config/config.toml"
  fi
  if [ -f /app/config/app.toml ]; then
      cp /app/config/app.toml "$CHAIN_HOME/config/app.toml"
  fi
fi

echo "Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf