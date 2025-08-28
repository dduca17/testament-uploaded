#!/usr/bin/env python3
# MIT License
import base64, json, os, sys, pathlib
from nacl.signing import SigningKey

ROOT = pathlib.Path(__file__).resolve().parent
KEYS = ROOT / "keys"
PUBS = ROOT / "pubkeys.json"

def main():
    if len(sys.argv) < 2:
        print("Usage: python chain_init.py <SIGNER_NAME>", file=sys.stderr); sys.exit(1)
    signer = sys.argv[1].strip()
    KEYS.mkdir(parents=True, exist_ok=True)
    sk = SigningKey.generate(); vk = sk.verify_key
    sk_b64 = base64.b64encode(bytes(sk)).decode("utf-8")
    vk_b64 = base64.b64encode(bytes(vk)).decode("utf-8")
    (KEYS / f"{signer}.ed25519.sk").write_text(sk_b64 + "\n", encoding="utf-8")
    pubs = json.loads(PUBS.read_text(encoding="utf-8")) if PUBS.exists() else {}
    pubs[signer] = vk_b64
    PUBS.write_text(json.dumps(pubs, indent=2, sort_keys=True), encoding="utf-8")
    gi = ROOT / ".gitignore"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    lines = set(existing.splitlines()); lines.update({"keys/*.sk", "*.env"})
    gi.write_text("\n".join(sorted([l for l in lines if l.strip()])) + "\n", encoding="utf-8")
    print(f"[+] Generated key for signer '{signer}'")
    print(f"[+] Public key saved in pubkeys.json")

if __name__ == "__main__":
    main()
