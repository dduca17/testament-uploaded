Fabric — One-Click Runner

1) Unzip this into your repo (same folder as STORY.md / PDFs / CHECKSUMS.txt).
2) macOS/Linux:
   chmod +x run.sh
   ./run.sh "Keeper" "Release v1.0.0" "The Fabric Story"

   Windows (PowerShell):
   .\run.ps1 -Signer Keeper -Note "Release v1.0.0" -Title "The Fabric Story"

Notes:
- The uploader runs in DRY-RUN mode by default. Remove --dry-run inside run.sh/run.ps1 to actually upload.
- Fill .env with your tokens before real uploads.
- The chain tools will append and verify a signed block in chain/CHAIN.jsonl.
