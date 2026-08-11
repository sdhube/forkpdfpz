#!/usr/bin/env bash
set -euo pipefail
PYTHON=${PYTHON:-python3}
export PYTHONPATH="${PYTHONPATH:-.}:$PWD"
 
$PYTHON -c "import pathlib, pprint, click, logger, class_book_manifest, class_actions_books, yaml_actions; print('All imports succeeded')"
 
