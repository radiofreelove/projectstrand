#!/usr/bin/env bash
# Build command for Cloudflare Pages:  bash scripts/cloudflare_build.sh
# Output directory:                   public
#
# Builds the site with clean URLs and runs the fast checks, so a broken build
# never deploys. Browser and axe-core checks run in GitHub Actions instead,
# because the Cloudflare build image has no browser.
set -euo pipefail

python3 --version
python3 -m pip install --quiet -r requirements.txt

# Optional font. Exit code 2 means the download failed: keep going with system
# fonts. Exit code 1 means a checksum mismatch: stop.
set +e
python3 scripts/fetch_fonts.py
code=$?
set -e
if [ "$code" -eq 1 ]; then
  echo "Font checksum mismatch. Stopping the build."
  exit 1
fi

CLEAN_URLS=1 python3 build.py
python3 tests/check_site.py
python3 tests/contrast.py
python3 tests/readability.py
