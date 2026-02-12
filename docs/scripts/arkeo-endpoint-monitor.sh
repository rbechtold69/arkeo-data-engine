#!/bin/bash
# Arkeo Endpoint Health Monitor & Failover
# Monitors the primary Arkeo endpoint used by sentinel.
# If primary goes down, automatically switches to the next healthy fallback.
#
# Usage: ./arkeo-endpoint-monitor.sh /path/to/sentinel-config.yaml
# Recommended: Run via cron every 2 minutes or as a systemd timer.
#
# Install:
#   chmod +x arkeo-endpoint-monitor.sh
#   crontab -e → */2 * * * * /path/to/arkeo-endpoint-monitor.sh /root/.arkeo/config.yaml >> /var/log/arkeo-failover.log 2>&1

set -euo pipefail

CONFIG_FILE="${1:-/root/.arkeo/config.yaml}"
TIMEOUT=5
MAX_RETRIES=2
LOG_PREFIX="[arkeo-failover]"

# ── Parse config ──────────────────────────────────────────────
if [ ! -f "$CONFIG_FILE" ]; then
  echo "$LOG_PREFIX ERROR: Config file not found: $CONFIG_FILE"
  exit 1
fi

# Extract current primary endpoint
CURRENT_PRIMARY=$(grep '^hub_provider_uri:' "$CONFIG_FILE" | awk '{print $2}' | tr -d '"' | tr -d "'")

# Extract fallback endpoints
FALLBACKS=()
in_fallbacks=false
while IFS= read -r line; do
  if echo "$line" | grep -q '^hub_provider_fallbacks:'; then
    in_fallbacks=true
    continue
  fi
  if $in_fallbacks; then
    if echo "$line" | grep -q '^  - '; then
      url=$(echo "$line" | sed 's/^  - //' | tr -d '"' | tr -d "'" | xargs)
      FALLBACKS+=("$url")
    else
      in_fallbacks=false
    fi
  fi
done < "$CONFIG_FILE"

if [ -z "$CURRENT_PRIMARY" ]; then
  echo "$LOG_PREFIX ERROR: No hub_provider_uri found in config"
  exit 1
fi

# ── Health check function ─────────────────────────────────────
check_endpoint() {
  local url="$1"
  local test_url="${url%/}/cosmos/base/tendermint/v1beta1/node_info"
  
  for attempt in $(seq 1 $MAX_RETRIES); do
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$test_url" 2>/dev/null || echo "000")
    
    if [ "$http_code" = "200" ]; then
      return 0
    fi
    
    if [ "$attempt" -lt "$MAX_RETRIES" ]; then
      sleep 2
    fi
  done
  
  return 1
}

# ── Check primary ─────────────────────────────────────────────
if check_endpoint "$CURRENT_PRIMARY"; then
  # Primary is healthy, nothing to do
  exit 0
fi

echo "$LOG_PREFIX $(date -u +%Y-%m-%dT%H:%M:%SZ) WARNING: Primary endpoint DOWN: $CURRENT_PRIMARY"

# ── Try fallbacks ─────────────────────────────────────────────
if [ ${#FALLBACKS[@]} -eq 0 ]; then
  echo "$LOG_PREFIX ERROR: No fallback endpoints configured. Sentinel may be unable to verify contracts."
  exit 1
fi

for fallback in "${FALLBACKS[@]}"; do
  echo "$LOG_PREFIX Trying fallback: $fallback"
  
  if check_endpoint "$fallback"; then
    echo "$LOG_PREFIX SUCCESS: Switching to $fallback"
    
    # Build new fallback list: old primary + other fallbacks (excluding new primary)
    NEW_FALLBACKS=("$CURRENT_PRIMARY")
    for fb in "${FALLBACKS[@]}"; do
      if [ "$fb" != "$fallback" ]; then
        NEW_FALLBACKS+=("$fb")
      fi
    done
    
    # Update config file
    # 1. Replace primary
    sed -i "s|^hub_provider_uri:.*|hub_provider_uri: $fallback|" "$CONFIG_FILE"
    
    # 2. Replace fallbacks section
    # Remove existing fallbacks
    sed -i '/^hub_provider_fallbacks:/,/^[^ ]/{ /^hub_provider_fallbacks:/d; /^  - /d; }' "$CONFIG_FILE"
    
    # Add new fallbacks after hub_provider_uri line
    FALLBACK_BLOCK="hub_provider_fallbacks:"
    for nfb in "${NEW_FALLBACKS[@]}"; do
      FALLBACK_BLOCK="$FALLBACK_BLOCK\n  - $nfb"
    done
    sed -i "/^hub_provider_uri:/a\\$FALLBACK_BLOCK" "$CONFIG_FILE"
    
    # 3. Restart sentinel
    # Try common restart methods
    if command -v supervisorctl &>/dev/null; then
      supervisorctl restart sentinel 2>/dev/null && echo "$LOG_PREFIX Sentinel restarted via supervisorctl" || true
    fi
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q arkeo; then
      CONTAINER=$(docker ps --format '{{.Names}}' | grep arkeo | head -1)
      docker exec "$CONTAINER" supervisorctl restart sentinel 2>/dev/null && echo "$LOG_PREFIX Sentinel restarted inside container $CONTAINER" || true
    fi
    if systemctl is-active sentinel &>/dev/null; then
      systemctl restart sentinel && echo "$LOG_PREFIX Sentinel restarted via systemd" || true
    fi
    
    echo "$LOG_PREFIX FAILOVER COMPLETE: $CURRENT_PRIMARY → $fallback at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    exit 0
  else
    echo "$LOG_PREFIX Fallback $fallback is also DOWN"
  fi
done

echo "$LOG_PREFIX CRITICAL: ALL endpoints are down. Primary and all ${#FALLBACKS[@]} fallbacks unreachable."
echo "$LOG_PREFIX Sentinel cannot verify contracts. Manual intervention required."
exit 2
