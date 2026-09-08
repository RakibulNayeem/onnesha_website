#!/usr/bin/env bash
set -e

# Vercel build step.
# Vercel's image marks its Python as "externally managed" (PEP 668), so a
# plain `pip install` is refused. Try the override first, fall back to a
# normal install on images that don't need it.
PY="${PYTHON:-python3.12}"
command -v "$PY" >/dev/null 2>&1 || PY=python3

echo "Using interpreter: $($PY --version)"

"$PY" -m pip install --break-system-packages -r requirements.txt \
  || "$PY" -m pip install -r requirements.txt

"$PY" -c "import django; print('Django', django.get_version(), 'installed OK')"
"$PY" manage.py collectstatic --noinput --clear
