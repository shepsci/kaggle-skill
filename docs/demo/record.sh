#!/usr/bin/env bash
# Record the README screencast with asciinema. See demo-script.md for the
# matching command sequence to run inside the recording.

set -euo pipefail

if ! command -v asciinema >/dev/null 2>&1; then
    echo "[FAIL] asciinema not installed. Install with:"
    echo "  brew install asciinema     # macOS"
    echo "  pip install asciinema      # any platform"
    exit 1
fi

OUTPUT="$(dirname "$0")/install-and-demo.cast"

echo "Recording to: $OUTPUT"
echo ""
echo "When the cast starts, run the commands from demo-script.md inside a"
echo "fresh Claude Code session. Press Ctrl+D when done."
echo ""
read -r -p "Press Enter to start recording..."

asciinema rec "$OUTPUT" \
    --title "kaggle-skill v2.1.0 — install + demo" \
    --idle-time-limit 1.5 \
    --rows 30 --cols 100

echo ""
echo "Recording saved to: $OUTPUT"
echo ""
echo "Upload to asciinema.org with:"
echo "  asciinema upload $OUTPUT"
echo ""
echo "Then update README.md to replace PLACEHOLDER with the cast id."
