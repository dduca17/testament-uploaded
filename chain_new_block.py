#!/usr/bin/env python3
# MIT License
import os, sys, json, base64, hashlib, pathlib, argparse
from datetime import datetime, timezone
from nacl.signing import SigningKey
from nacl.encoding import RawEncoder

ROOT = pathlib.Path(__file__).resolve().parent
LEDGER = ROOT / "chain" / "CHAIN.jsonl"
PUBS = ROOT / "chain" / "pubkeys.json"
KEYS = ROOT / "chain" / "keys"

def sha256hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def file_sha256(path: pathlib.Path) -> tuple[int, str]:
    h = hashlib.sha256(); n = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            n += len(chunk); h.update(chunk)
    return n, h.hexdigest()

def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode("utf-8")

def merkle_root(hashes: list[str]) -> str:
    if not hashes: return sha256hex(b'')
    level = [bytes.fromhex(h) for h in hashes]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            left = level[i]; right = level[i+1] if i+1 < len(level) else level[i]
            nxt.append(hashlib.sha256(left + right).digest())
        level = nxt
    return level[0].hex()

def load_prev():
    if not LEDGER.exists(): return None, -1
    last = None; idx = -1
    with open(LEDGER, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if line.strip(): last = json.loads(line); idx = i
    return last, idx

def main():
    ap = argparse.ArgumentParser(description="Create a new signed Fabric block")
    ap.add_argument("--signer", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--file", action="append", required=True)
    args = ap.parse_args()

    sk_path = KEYS / f"{args.signer}.ed25519.sk"
    if not sk_path.exists():
        print(f"[!] Secret key not found: {sk_path} — run: python chain_init.py {args.signer}", file=sys.stderr); sys.exit(1)
    sk_b64 = sk_path.read_text().strip(); sk = SigningKey(base64.b64decode(sk_b64))

    pubs = json.loads(PUBS.read_text(encoding="utf-8")) if PUBS.exists() else {}
    vk_b64 = pubs.get(args.signer)
    if not vk_b64:
        print(f"[!] No pubkey entry for signer '{args.signer}' in pubkeys.json", file=sys.stderr); sys.exit(1)

    prev, idx = load_prev(); index = idx + 1; prev_hash = prev["block_hash"] if prev else None

    files = []; leaves = []
    for p in args.file:
        pp = pathlib.Path(p)
        if not pp.exists(): print(f"[!] Missing file: {pp}", file=sys.stderr); sys.exit(1)
        size, digest = file_sha256(pp); files.append({"path": str(pp), "bytes": size, "sha256": digest}); leaves.append(digest)

    block = {
        "schema": "fabric-chain/1.0",
        "index": index,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prev_hash": prev_hash,
        "files": files,
        "merkle_root": merkle_root(leaves),
        "notes": args.note,
    }
    block_hash = sha256hex(canonical(block)); block["block_hash"] = block_hash
    sig = sk.sign(bytes.fromhex(block_hash), encoder=RawEncoder).signature
    sig_b64 = base64.b64encode(sig).decode("utf-8")
    block["signatures"] = [{"signer": args.signer, "pubkey_b64": vk_b64, "sig_b64": sig_b64}]
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(block, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"[+] Block {index} appended"); print(f"    hash: {block_hash}"); 
    if prev_hash: print(f"    prev: {prev_hash}")

if __name__ == "__main__":
    main()
