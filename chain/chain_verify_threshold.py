#!/usr/bin/env python3
import json, base64, hashlib, sys, pathlib, os
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

ROOT   = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "chain" / "CHAIN.jsonl"
PUBS   = ROOT / "chain" / "pubkeys.json"
POLICY = ROOT / "chain" / "policy.json"

def sha256hex(b): import hashlib; return hashlib.sha256(b).hexdigest()
def canonical(o): return json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
def merkle_root(hashes):
    import hashlib as _h
    if not hashes: return _h.sha256(b'').hexdigest()
    level=[bytes.fromhex(h) for h in hashes]
    while len(level)>1:
        nxt=[]; 
        for i in range(0,len(level),2):
            l=level[i]; r=level[i+1] if i+1<len(level) else l
            nxt.append(_h.sha256(l+r).digest())
        level=nxt
    return level[0].hex()

def main():
    if not LEDGER.exists(): print("[!] No chain yet: chain/CHAIN.jsonl"); sys.exit(1 if os.getenv("GITHUB_ACTIONS") else 0)
    pubs   = json.loads(PUBS.read_text(encoding="utf-8")) if PUBS.exists() else {}
    policy = json.loads(POLICY.read_text(encoding="utf-8")) if POLICY.exists() else {}
    allowed   = set(policy.get("allowed_signers", []))
    threshold = int(policy.get("threshold", 1))

    prev_hash=None; prev_index=-1; ok=True

    with open(LEDGER,"r",encoding="utf-8") as f:
        for lineno,line in enumerate(f, start=1):
            if not line.strip(): continue
            b=json.loads(line); idx=b["index"]
            if idx != prev_index+1: print(f"[!] Index jump at line {lineno}: {idx} after {prev_index}"); ok=False
            if prev_hash is not None and b["prev_hash"] != prev_hash: print(f"[!] prev_hash mismatch at block {idx}"); ok=False
            leaves=[fi["sha256"] for fi in b["files"]]
            if b["merkle_root"] != merkle_root(leaves): print(f"[!] merkle_root mismatch at block {idx}"); ok=False
            to_hash={k:v for k,v in b.items() if k not in ("signatures","block_hash")}
            calc=sha256hex(canonical(to_hash))
            if calc != b["block_hash"]: print(f"[!] block_hash mismatch at block {idx}"); ok=False

            sigs=b.get("signatures", [])
            if not sigs: print(f"[!] no signatures at block {idx}"); ok=False

            valid=0
            for s in sigs:
                signer=s["signer"]; pub_b64=s["pubkey_b64"]; sig_b64=s["sig_b64"]
                if allowed and signer not in allowed:
                    print(f"[!] signer '{signer}' not in allowed_signers at block {idx}"); continue
                try:
                    VerifyKey(base64.b64decode(pub_b64)).verify(
                        bytes.fromhex(b["block_hash"]), base64.b64decode(sig_b64)
                    ); valid += 1
                except BadSignatureError:
                    print(f"[!] bad signature from '{signer}' at block {idx}")
            if valid < threshold:
                print(f"[!] signature threshold not met at block {idx}: {valid}/{threshold} valid"); ok=False

            prev_hash=b["block_hash"]; prev_index=idx

    print("[✓] Chain verified OK" if ok else "[x] Chain verification FAILED")
    sys.exit(0 if ok else 1)

if __name__=="__main__": main()
