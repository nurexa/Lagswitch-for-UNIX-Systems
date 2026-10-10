#!/bin/sh
# Usage: ./install.sh [uninstall]
set -e
LIB=/usr/local/lib/lagswitch BIN=/usr/local/bin/lagswitch
if [ "$1" = uninstall ]; then sudo rm -rf "$LIB" "$BIN"; echo "removed"; exit; fi
for c in nft tc ip python3; do command -v $c >/dev/null || { echo "missing: $c"; exit 1; }; done
sudo rm -rf "$LIB" && sudo mkdir -p "$LIB" && sudo cp -r lagswitch "$LIB/"
printf '#!/bin/sh\nPYTHONPATH=%s exec python3 -m lagswitch "$@"\n' "$LIB" | sudo tee "$BIN" >/dev/null
sudo chmod +x "$BIN"
echo "installed. try: sudo lagswitch run --key f8"
