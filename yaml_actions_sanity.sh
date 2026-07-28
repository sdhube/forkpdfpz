#!/usr/bin/env bash
set -euo pipefail

# Script to sanity-check that Python can import the modules used by yaml_actions.py
# Usage: ./yaml_actions_sanity.sh
# Ensure it's run from the repository root so local modules (logger, class_books_actions, etc.)
# are importable. You can also run with PYTHON=python3 to pick a specific python executable.

PYTHON=${PYTHON:-python3}
# Ensure current repo root is on PYTHONPATH so local modules import correctly
export PYTHONPATH="${PYTHONPATH:-.}:$PWD"

$PYTHON - <<'PY'
import importlib, sys, traceback

modules = [
    'pathlib',
    'pprint',
    'click',
    'logger',
    'class_books_actions',
    'class_book_manifest',
]

ok = []
failed = []

for m in modules:
    try:
        importlib.import_module(m)
        ok.append(m)
    except Exception:
        failed.append((m, traceback.format_exc()))

print('Imported OK: {}'.format(', '.join(ok) if ok else '<none>'))

if failed:
    print('\nFailures:')
    for m, tb in failed:
        print('--- {} ---'.format(m))
        print(tb)
    sys.exit(1)
else:
    print('\nAll imports succeeded')

PY

exit 0
