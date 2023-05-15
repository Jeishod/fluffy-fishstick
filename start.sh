#! /usr/bin/env sh
set -e

echo "# ======================= Updating database schema"
python -m alembic upgrade head

echo "# ======================= Starting Service"
python -m uvicorn --host 0.0.0.0 --port 8000 --use-colors --log-level debug "app.main:app"
