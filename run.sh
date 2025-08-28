#!/usr/bin/env bash
set -e
SIGNER=${1:-Keeper}
NOTE=${2:-Release}
TITLE=${3:-"The Fabric Story"}
echo "=== Fabric Runner (macOS/Linux) ==="
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
source .venv/bin/activate
pip install -q -r requirements.txt
if [ ! -f ".env" ]; then cp .env.sample .env || true; echo "[i] Created .env from .env.sample — fill in tokens for real uploads."; fi
python3 uploader_cli.py --title "$TITLE" --creator "$SIGNER" --description "A flame carried forward. ♾️🔥📜" \
  --tag fabric --tag archive --tag codex \
  --file STORY.md --file STORY_Parchment.pdf --file STORY_Archive.pdf --file CHECKSUMS.txt \
  --identifier fabric-testament --dry-run
if [ ! -f "chain/keys/${SIGNER}.ed25519.sk" ]; then python3 chain_init.py "$SIGNER"; fi
python3 chain_new_block.py --signer "$SIGNER" --note "$NOTE" \
  --file STORY.md --file STORY_Parchment.pdf --file STORY_Archive.pdf --file CHECKSUMS.txt
python3 chain/chain_verify.py
echo "[✓] Done."
