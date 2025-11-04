#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
/usr/bin/env python3 packaging/make_mac_app.py "$@"
