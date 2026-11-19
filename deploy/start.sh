#!/bin/sh
# Container start for the one-process deployment (deploy/server.py, DEPLOY.md).
# Migrates, loads the policies, starts the server, then seeds the demo data. The mocks keep
# their state in memory, so every start resets the business tables and the mocks together.
set -eu

PORT="${PORT:-10000}"
export MOCK_PAYMENTS_URL="http://127.0.0.1:$PORT/mock/payments"
export MOCK_SHIPPING_URL="http://127.0.0.1:$PORT/mock/shipping"
export MOCK_TICKETING_URL="http://127.0.0.1:$PORT/mock/ticketing"

python -m alembic upgrade head
if [ -n "${EVAL_DATABASE_URL:-}" ]; then
    DATABASE_URL="$EVAL_DATABASE_URL" python -m alembic upgrade head
fi
# Policies are ingested by the server's warm-up (deploy/server.py): the model loads once.
uvicorn deploy.server:app --host 0.0.0.0 --port "$PORT" \
    --proxy-headers --forwarded-allow-ips '*' &
server=$!
trap 'kill -TERM "$server" 2>/dev/null' TERM INT

tries=0
until python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$PORT/health', timeout=2)" 2>/dev/null; do
    tries=$((tries + 1))
    # The warm-up loads the model before the port opens: minutes on a small shared CPU.
    if [ "$tries" -gt 600 ]; then
        echo "server did not become healthy" >&2
        kill -TERM "$server" 2>/dev/null
        exit 1
    fi
    sleep 1
done

python -m scripts.seed_data --push-mocks
wait "$server"
