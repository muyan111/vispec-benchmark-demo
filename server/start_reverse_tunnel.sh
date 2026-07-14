#!/usr/bin/env bash
set -euo pipefail

WINDOWS_VPN_IP="${1:-}"
WINDOWS_USER="${WINDOWS_USER:-dell}"
WINDOWS_PORT="${WINDOWS_PORT:-22}"
LOCAL_SSH_PORT="${LOCAL_SSH_PORT:-2224}"
WINDOWS_FORWARD_PORT="${WINDOWS_FORWARD_PORT:-2225}"
KEY="${KEY:-/root/.ssh/vispec_tunnel_ed25519}"
LOG="${LOG:-/root/.ssh/vispec_reverse_tunnel.log}"

if [ -z "$WINDOWS_VPN_IP" ]; then
  echo "Usage: bash server/start_reverse_tunnel.sh <Windows-CorpLink-IP>"
  exit 2
fi

if [ ! -f "$KEY" ]; then
  echo "Tunnel key not found: $KEY"
  exit 1
fi

pkill -f "vispec_tunnel_ed25519.*-R ${WINDOWS_FORWARD_PORT}:127.0.0.1:${LOCAL_SSH_PORT}" 2>/dev/null || true

nohup ssh -i "$KEY" \
  -p "$WINDOWS_PORT" \
  -o BatchMode=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ConnectTimeout=15 \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/root/.ssh/vispec_windows_known_hosts \
  -o ExitOnForwardFailure=yes \
  -N -C -R "${WINDOWS_FORWARD_PORT}:127.0.0.1:${LOCAL_SSH_PORT}" \
  "${WINDOWS_USER}@${WINDOWS_VPN_IP}" > "$LOG" 2>&1 &

sleep 3
cat "$LOG"
echo "Reverse tunnel requested on Windows localhost:${WINDOWS_FORWARD_PORT}"
