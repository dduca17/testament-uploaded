#!/usr/bin/env python3
# MIT License
import json, base64, hashlib, sys, pathlib
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

ROOT = pathlib.Path(__file__).resolve().parent
LEDGER = ROOT / "chain" / "CHAIN.jsonl"
PUBS = ROOT / "chain" / "pubkeys.json"

def sha256hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode("utf-8")

def merkle_root(hashes: list[str]) -> str:
    import hashlib as _h
    if not hashes: return _h.sha256(b'').hexdigest()
    level = [bytes.fromhex(h) for h in hashes]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            l = level[i]; r = level[i+1] if i+1 < len(level) else l
            nxt.append(_h.sha256(l + r).digest())
        level = nxt
    return level[0].hex()

def main():
    if not LEDGER.exists():
        print("[i] No chain yet."); sys.exit(0)
    pubs = json.loads(PUBS.read_text(encoding="utf-8")) if PUBS.exists() else {}
    prev_hash = None; prev_index = -1; ok = True
    with open(LEDGER, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip(): continue
            block = json.loads(line); idx = block["index"]
            if idx != prev_index + 1:
                print(f"[!] Index jump at line {lineno}: {idx} after {prev_index}"); ok = False
            if block["prev_hash"] != prev_hash:
                print(f"[!] prev_hash mismatch at block {idx}"); ok = False
            leaves = [fi["sha256"] for fi in block["files"]]
            if block["merkle_root"] != merkle_root(leaves):
                print(f"[!] merkle_root mismatch at block {idx}"); ok = False
            to_hash = {k:v for k,v in block.items() if k not in ("signatures","block_hash")}
            calc_hash = sha256hex(canonical(to_hash))
            if calc_hash != block["block_hash"]:
                print(f"[!] block_hash mismatch at block {idx}"); ok = False
            sigs = block.get("signatures", [])
            if not sigs: print(f"[!] no signatures at block {idx}"); ok = False
            for s in sigs:
                signer = s["signer"]; pub_b64 = s["pubkey_b64"]; sig_b64 = s["sig_b64"]
                known = pubs.get(signer)
                if known != pub_b64:
                    print(f"[!] pubkey mismatch for signer '{signer}' at block {idx}"); ok = False; continue
                try:
                    VerifyKey(base64.b64decode(pub_b64)).verify(bytes.fromhex(block["block_hash"]), base64.b64decode(sig_b64))
                except BadSignatureError:
                    print(f"[!] bad signature from '{signer}' at block {idx}"); ok = False
            prev_hash = block["block_hash"]; prev_index = idx
    if ok:
        print("[✓] Chain verified OK"); sys.exit(0)
    else:
        print("[x] Chain verification FAILED"); sys.exit(1)

if __name__ == "__main__":
    main()
