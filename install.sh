#!/bin/sh
# Resolve the checkout directory so the installer works from any working directory.
set -eu
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$script_dir/install.py" "$@"
