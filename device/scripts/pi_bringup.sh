#!/usr/bin/env bash
# Thin wrapper — canonical script lives in ops/scripts/pi_bringup.sh
exec "$(cd "$(dirname "$0")/../.." && pwd)/ops/scripts/pi_bringup.sh" "$@"
