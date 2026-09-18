#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${DEPLOY_HOST:-debian}"
REMOTE_ROOT="${DEPLOY_PATH:-/home/tu/hosting/vlearn-notebooklm}"

if [[ ! -d materials/raw || ! -d materials/derived ]]; then
  echo "Expected materials/raw and materials/derived in the repository checkout." >&2
  exit 1
fi

ssh "$REMOTE_HOST" "mkdir -p '$REMOTE_ROOT/materials/raw' '$REMOTE_ROOT/materials/derived'"
rsync -az --human-readable materials/raw/ "$REMOTE_HOST:$REMOTE_ROOT/materials/raw/"
rsync -az --human-readable materials/derived/ "$REMOTE_HOST:$REMOTE_ROOT/materials/derived/"

echo "Lecture artifacts synced to $REMOTE_HOST:$REMOTE_ROOT/materials"
