#!/bin/sh
set -e

# 1. Wait for database readiness
if [ "${WAIT_FOR_DB:-True}" = "True" ]; then
  echo "[gabu-entrypoint] Checking database connectivity..."
  python - <<'PY'
import os
import sys
import time
import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.production"),
)
django.setup()

from django.db import connections
from django.db.utils import OperationalError

for attempt in range(30):
    try:
        connections["default"].ensure_connection()
        print("[gabu-entrypoint] Database connection ready.")
        sys.exit(0)
    except OperationalError as exc:
        print(f"[gabu-entrypoint] Waiting for database ({attempt + 1}/30): {exc}")
        time.sleep(2)

print("[gabu-entrypoint] ERROR: Database did not become ready within 60 seconds.", file=sys.stderr)
sys.exit(1)
PY
fi

# 2. Schema migration & initial data bootstrap (skipped on auxiliary worker containers via SKIP_DB_INIT=True)
if [ "${SKIP_DB_INIT:-False}" != "True" ]; then
  echo "[gabu-entrypoint] Applying database migrations..."
  python manage.py migrate --noinput

  echo "[gabu-entrypoint] Bootstrapping RBAC roles & accounts..."
  if [ "${AUTO_SEED_DEMO_LAB:-False}" = "True" ]; then
    python manage.py bootstrap_roles --create-demo-users --ensure-superuser
  else
    python manage.py bootstrap_roles --ensure-superuser
  fi

  if [ "${AUTO_SEED_ROUTING:-True}" = "True" ]; then
    echo "[gabu-entrypoint] Ensuring starter routing profiles exist (if empty)..."
    python manage.py seed_default_routing --only-if-empty
  fi

  echo "[gabu-entrypoint] Initializing BGP router configuration..."
  if [ "${AUTO_SEED_DEMO_LAB:-False}" = "True" ]; then
    python manage.py seed_dev_lab
  else
    python manage.py bootstrap_bgp_config
  fi
fi

# 3. Collect static assets when enabled (Production Gunicorn + Nginx)
if [ "${COLLECT_STATIC:-False}" = "True" ]; then
  echo "[gabu-entrypoint] Collecting static files..."
  python manage.py collectstatic --noinput
fi

echo "[gabu-entrypoint] Launching: $*"
exec "$@"
