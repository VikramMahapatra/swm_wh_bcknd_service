#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "usage: start-api.sh <package> [entrypoint]"
  exit 1
fi

PACKAGE="$1"
ENTRYPOINT="${2:-$1}"
WAIT_FOR_HOSTS="${WAIT_FOR_HOSTS:-}"
WAIT_FOR_TIMEOUT_SECS="${WAIT_FOR_TIMEOUT_SECS:-120}"

if [ -n "$WAIT_FOR_HOSTS" ]; then
  echo "[startup] waiting for dependencies: $WAIT_FOR_HOSTS"
  python - "$WAIT_FOR_HOSTS" "$WAIT_FOR_TIMEOUT_SECS" <<'PY'
import socket
import sys
import time

hosts = [item.strip() for item in sys.argv[1].split(",") if item.strip()]
timeout = int(sys.argv[2])
start = time.time()

for item in hosts:
    if ":" not in item:
        print(f"invalid dependency '{item}', expected host:port", file=sys.stderr)
        sys.exit(2)
    host, port_s = item.rsplit(":", 1)
    port = int(port_s)

    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"[startup] dependency ready: {host}:{port}")
                break
        except OSError:
            if time.time() - start > timeout:
                print(f"timeout waiting for {host}:{port}", file=sys.stderr)
                sys.exit(1)
            time.sleep(1)
PY
fi

touch /tmp/app-ready
echo "[startup] launching API package=${PACKAGE} entrypoint=${ENTRYPOINT}"
exec uv run --package "$PACKAGE" "$ENTRYPOINT"
