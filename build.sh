#!/usr/bin/env bash
# Packs the add-on into dist/tap-to-rate.ankiaddon, the file to send to the
# iPad (AirDrop, iCloud Drive, ...) and install with Tools > Add-ons >
# Install from file...
set -euo pipefail
cd "$(dirname "$0")"

shipped=(__init__.py manifest.json config.json config.md)
for file in "${shipped[@]}"; do
    [ -f "$file" ] || { echo "missing $file" >&2; exit 1; }
done

rm -rf dist
mkdir -p dist
zip -X -q dist/tap-to-rate.ankiaddon "${shipped[@]}"

echo "built dist/tap-to-rate.ankiaddon"
unzip -l dist/tap-to-rate.ankiaddon
