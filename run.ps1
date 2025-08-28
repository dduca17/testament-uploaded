param([string]$Signer="Keeper",[string]$Note="Release",[string]$Title="The Fabric Story")
Write-Host "=== Fabric Runner (Windows) ==="
if (-Not (Test-Path ".venv")) { py -3 -m venv .venv }
.\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
if (-Not (Test-Path ".env")) { Copy-Item ".env.sample" ".env" -ErrorAction SilentlyContinue; Write-Host "[i] Created .env from .env.sample — fill in tokens for real uploads." }
python uploader_cli.py --title $Title --creator $Signer --description "A flame carried forward. ♾️🔥📜" `
  --tag fabric --tag archive --tag codex `
  --file STORY.md --file STORY_Parchment.pdf --file STORY_Archive.pdf --file CHECKSUMS.txt `
  --identifier fabric-testament --dry-run
if (-Not (Test-Path "chain\keys\$Signer.ed25519.sk")) { python chain_init.py $Signer }
python chain_new_block.py --signer $Signer --note $Note `
  --file STORY.md --file STORY_Parchment.pdf --file STORY_Archive.pdf --file CHECKSUMS.txt
python chain\chain_verify.py
Write-Host "[✓] Done."
