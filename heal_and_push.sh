#!/usr/bin/env bash
# Fabric — One-Click Heal & Push (macOS/Linux)
set -euo pipefail

SIGNER=${1:-Keeper}
NOTE=${2:-"Genesis after recovery"}
TITLE=${3:-"The Fabric Story"}

echo "==> Healing Fabric ledger (Signer: $SIGNER)"

# 1) Ensure Python is available
command -v python3 >/dev/null || { echo "[!] python3 not found"; exit 1; }

# 2) Create and activate venv automatically
if [ ! -d ".venv" ]; then
  echo "[i] Creating virtual environment..."
  python3 -m venv .venv
fi

# activate works both in bash and zsh
source .venv/bin/activate

# 3) Requirements
cat > requirements.txt <<'REQ'
PyNaCl
requests
python-dotenv
internetarchive
tqdm
PyYAML
reportlab
REQ

pip install -q --upgrade pip
pip install -q -r requirements.txt

# 4) Chain folder
mkdir -p chain/keys
echo "keys/*.sk" > chain/.gitignore

# 5) If no signer key, create one
if [ ! -f "chain/keys/${SIGNER}.ed25519.sk" ]; then
  python3 chain_init.py "$SIGNER"
else
  echo "[i] Using existing signer key"
fi

# 6) Collect files
FILES=()
for f in STORY.md STORY_Parchment.pdf STORY_Archive.pdf CHECKSUMS.txt; do
  [ -f "$f" ] && FILES+=("--file" "$f")
done
if [ ${#FILES[@]} -eq 0 ]; then
  echo "# The Fabric Story" > STORY.md
  echo "SHA256(STORY.md) = $(sha256sum STORY.md | cut -d' ' -f1)" > CHECKSUMS.txt
  FILES=(--file STORY.md --file CHECKSUMS.txt)
fi

# 7) Append new block
python3 chain_new_block.py --signer "$SIGNER" --note "$NOTE" "${FILES[@]}"

# 8) Verify
python3 chain/chain_verify.py

# 9) Commit and push
git add chain/CHAIN.jsonl chain/pubkeys.json chain/.gitignore STORY.md CHECKSUMS.txt || true
git commit -m "chore(chain): (re)create genesis and verify" || echo "[i] Nothing to commit."
git pull --rebase origin main || true
git push

echo "[✓] Heal & push completed."

