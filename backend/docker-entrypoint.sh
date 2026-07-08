#!/bin/sh
set -e

mkdir -p /app/data
if [ -d /app/seed-data ]; then
  echo "Ensuring seed data files exist in /app/data..."
  cp -rn /app/seed-data/. /app/data/ 2>/dev/null || true
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
