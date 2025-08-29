#!/usr/bin/env python3
import json, base64, argparse, pathlib
from nacl.signing import SigningKey
from nacl.encoding import RawEncoder

LEDGER = pathlib.Path("chain/CHAIN.jsonl")
KEYS   = pathlib.Path("chain/keys")
PUBS   = pathlib.Path("chain/pubkeys.json")

def load_blocks():
    return [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]

def main():
    ap = argparse.ArgumentParser(description="Co-sign an existing block by index (default latest)")
    ap.add_argument("--signer", required=True, help="Signer name (must have a .sk key)")
    ap.add_argument("--index", type=int, default=None, help="Block index to co-sign (default latest)")
    args = ap.parse_args()

    assert LEDGER.exists(), "Missing chain/CHAIN.jsonl"
    skp = KEYS / f"{args.signer}.ed25519.sk"
    assert skp.exists(), f"Missing secret key: {skp}"

    blocks = load_blocks()
    b = blocks[-1] if args.index is None else next((x for x in blocks if x["index"] == args.index), None)
    assert b, "Block not found"

    sk = SigningKey(base64.b64decode(skp.read_text().strip()))
    sig_b64 = base64.b64encode(sk.sign(bytes.fromhex(b["block_hash"]), encoder=RawEncoder).signature).decode()

    pubs = json.loads(PUBS.read_text(encoding="utf-8")) if PUBS.exists() else {}
    pubs[args.signer] = base64.b64encode(sk.verify_key.encode()).decode()

    b.setdefault("signatures", [])
    b["signatures"] = [s for s in b["signatures"] if s.get("signer") != args.signer]
    b["signatures"].append({"signer": args.signer, "pubkey_b64": pubs[args.signer], "sig_b64": sig_b64})

    LEDGER.write_text("\n".join(json.dumps(x, sort_keys=True, ensure_ascii=False) for x in sorted(blocks, key=lambda x: x["index"])) + "\n",
                      encoding="utf-8")
    PUBS.write_text(json.dumps(pubs, indent=2, sort_keys=True), encoding="utf-8")

    print(f"[✓] Co-signed block {b['index']} as '{args.signer}'")

if __name__ == "__main__":
    main()
