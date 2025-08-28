#!/usr/bin/env python3
import json, base64, hashlib, sys, pathlib, os
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

ROOT   = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "chain" / "CHAIN.jsonl"
PUBS   = ROOT / "chain" / "pubkeys.json"

def sha256hex(b: bytes) -> str:
    import hashlib; return hashlib.sha256(b).hexdigest()

def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def merkle_root(hashes):
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

def to_list(v):
    if v is None: return []
    if isinstance(v, list): return v
    return [v]

def main():
    if not LEDGER.exists():
        msg = "[!] No chain yet: expected chain/CHAIN.jsonl"
        print(msg)
        sys.exit(1 if os.getenv("GITHUB_ACTIONS") else 0)

    allow = {}
    if PUBS.exists():
        raw = json.loads(PUBS.read_text(encoding="utf-8"))
        # normalize to lists
        allow = {k: to_list(v) for k, v in raw.items()}

    prev_hash, prev_index, ok = None, -1, True

    with open(LEDGER, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip(): continue
            block = json.loads(line); idx = block["index"]

            # index continuity
            if idx != prev_index + 1:
                print(f"[!] Index jump at line {lineno}: {idx} after {prev_index}"); ok = False

            # prev linkage
            if block["prev_hash"] != prev_hash and prev_hash is not None:
                print(f"[!] prev_hash mismatch at block {idx}"); ok = False

            # merkle
            leaves = [fi["sha256"] for fi in block["files"]]
            if block["merkle_root"] != merkle_root(leaves):
                print(f"[!] merkle_root mismatch at block {idx}"); ok = False

            # block hash
            to_hash = {k: v for k, v in block.items() if k not in ("signatures", "block_hash")}
            calc = sha256hex(canonical(to_hash))
            if calc != block["block_hash"]:
                print(f"[!] block_hash mismatch at block {idx}"); ok = False

            # signatures — verify with the key embedded in the block
            sigs = block.get("signatures", [])
            if not sigs:
                print(f"[!] no signatures at block {idx}"); ok = False
            for s in sigs:
                signer   = s["signer"]
                pub_b64  = s["pubkey_b64"]
                sig_b64  = s["sig_b64"]

                # cryptographic verification (source of truth)
                try:
                    VerifyKey(base64.b64decode(pub_b64)).verify(
                        bytes.fromhex(block["block_hash"]),
                        base64.b64decode(sig_b64)
                    )
                except BadSignatureError:
                    print(f"[!] bad signature from '{signer}' at block {idx}"); ok = False

                # allowlist advisory check (warn only)
                if signer in allow and allow[signer] and pub_b64 not in allow[signer]:
                    print(f"[i] WARN: signer '{signer}' used a pubkey not in pubkeys.json allowlist at block {idx}")

            prev_hash, prev_index = block["block_hash"], idx

    if ok:
        print("[✓] Chain verified OK"); sys.exit(0)
    else:
        print("[x] Chain verification FAILED"); sys.exit(1)

if __name__ == "__main__":
    main()

