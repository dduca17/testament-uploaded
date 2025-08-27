#!/usr/bin/env python3
# MIT License
from __future__ import annotations
import os, sys, time, json, hashlib, mimetypes, pathlib, logging
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm
from dotenv import load_dotenv

# Optional dependencies:
#   pip install internetarchive requests
import requests
import internetarchive as ia

log = logging.getLogger("testament.uploader")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

load_dotenv()

# ---------- Helpers ----------
def sha256sum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def build_checksums(files: List[str]) -> Dict[str, str]:
    return {os.path.basename(f): sha256sum(f) for f in files}

def ensure_paths(files: List[str]) -> List[str]:
    ok = []
    for f in files:
        if not os.path.exists(f):
            raise FileNotFoundError(f"File not found: {f}")
        ok.append(os.path.abspath(f))
    return ok

# ---------- Metadata ----------
def default_metadata(title: str,
                     creators: List[str],
                     description: str,
                     tags: List[str],
                     timestamp_label: str = "Stamped at 3:16 AM — Earth — Human") -> Dict:
    return {
        "title": title,
        "description": description.strip() + f"\n\n{timestamp_label}",
        "creators": creators,
        "keywords": tags,
        "license": "MIT",
        "notes": "Fabric Testament — ♾️🔥📜",
    }

# ---------- Internet Archive ----------
def upload_to_internet_archive(identifier: str,
                               files: List[str],
                               md: Dict,
                               retries: int = 3,
                               collection: Optional[str] = None,
                               mediatype: str = "texts") -> str:
    """
    Uses the 'internetarchive' library. Requires IA_ACCESS_KEY/IA_SECRET_KEY in environment.
    """
    ak = os.getenv("IA_ACCESS_KEY")
    sk = os.getenv("IA_SECRET_KEY")
    if not ak or not sk:
        raise RuntimeError("IA credentials missing (IA_ACCESS_KEY / IA_SECRET_KEY)")

    if collection is None:
        collection = os.getenv("IA_COLLECTION", "opensource")
    mediatype = os.getenv("IA_MEDIATYPE", mediatype)

    log.info(f"IA upload → id={identifier}, collection={collection}, mediatype={mediatype}")

    md_ia = {
        "collection": collection,
        "mediatype": mediatype,
        "subject": md.get("keywords", []),
        "creator": "; ".join(md.get("creators", [])),
        "title": md.get("title"),
        "description": md.get("description"),
        "licenseurl": "https://opensource.org/licenses/MIT",
    }

    item = ia.get_item(identifier)
    for attempt in range(1, retries + 1):
        try:
            r = item.upload(
                files,
                metadata=md_ia,
                access_key=ak,
                secret_key=sk,
                retries=5,
                verify=True,
                checksum=True,
                verbose=True,
            )
            if r.ok:
                url = f"https://archive.org/details/{identifier}"
                log.info(f"IA upload OK → {url}")
                return url
            else:
                raise RuntimeError(f"IA upload failed (status={r.status_code})")
        except Exception as e:
            log.warning(f"IA upload attempt {attempt}/{retries} failed: {e}")
            time.sleep(2 * attempt)
    raise RuntimeError("IA upload failed after retries")

# ---------- Zenodo ----------
ZENODO_API = "https://zenodo.org/api"
ZENODO_SANDBOX_API = "https://sandbox.zenodo.org/api"

def _zenodo_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

def upload_to_zenodo(files: List[str],
                     md: Dict,
                     publish: bool = True,
                     use_sandbox: bool = True) -> Tuple[str, Optional[str]]:
    """
    Creates a deposition, uploads files, sets metadata, and (optionally) publishes.
    Returns: (record_url, doi_or_none)
    """
    token = os.getenv("ZENODO_TOKEN")
    if not token:
        raise RuntimeError("ZENODO_TOKEN missing in environment")
    api = ZENODO_SANDBOX_API if (use_sandbox or os.getenv("ZENODO_SANDBOX") == "1") else ZENODO_API

    # 1) Create deposition
    r = requests.post(f"{api}/deposit/depositions", headers=_zenodo_headers(token), json={})
    r.raise_for_status()
    dep = r.json()
    dep_id = dep["id"]

    # 2) Upload files
    for f in tqdm(files, desc="Zenodo upload"):
        filename = os.path.basename(f)
        with open(f, "rb") as fp:
            r = requests.post(
                f"{api}/deposit/depositions/{dep_id}/files",
                headers=_zenodo_headers(token),
                data={"name": filename},
                files={"file": fp},
            )
            r.raise_for_status()

    # 3) Set metadata
    creators = [{"name": c} for c in md.get("creators", [])]
    payload = {
        "metadata": {
            "title": md.get("title"),
            "upload_type": "publication",
            "publication_type": "other",
            "description": md.get("description"),
            "creators": creators or [{"name": "Unknown"}],
            "keywords": md.get("keywords", []),
            "license": "mit",
            "notes": md.get("notes", ""),
        }
    }
    r = requests.put(f"{api}/deposit/depositions/{dep_id}",
                     headers=_zenodo_headers(token),
                     json=payload)
    r.raise_for_status()

    # 4) Publish (optional)
    if publish:
        r = requests.post(f"{api}/deposit/depositions/{dep_id}/actions/publish",
                          headers=_zenodo_headers(token))
        r.raise_for_status()
        dep = r.json()

    record_id = dep.get("record_id") or dep.get("id")
    # Best-effort to extract URL/DOI
    record_url = dep.get("links", {}).get("record_html") or dep.get("links", {}).get("html")
    doi = None
    for id_ in dep.get("metadata", {}).get("related_identifiers", []):
        if id_.get("scheme") == "doi":
            doi = id_.get("identifier")
            break
    # Alternate location for DOI
    doi = doi or dep.get("doi")

    if not record_url:
        # Construct a plausible URL
        base = "https://sandbox.zenodo.org/record" if (api == ZENODO_SANDBOX_API) else "https://zenodo.org/record"
        record_url = f"{base}/{record_id}"

    log.info(f"Zenodo OK → {record_url}")
    if doi:
        log.info(f"DOI → {doi}")
    return record_url, doi

# ---------- Orchestration ----------
def run_archive(
    title: str,
    creators: List[str],
    description: str,
    tags: List[str],
    files: List[str],
    identifier: Optional[str] = None,
    do_ia: bool = True,
    do_zenodo: bool = True,
    zenodo_publish: bool = True,
    zenodo_sandbox: bool = True,
    dry_run: bool = False
) -> Dict[str, Optional[str]]:
    files = ensure_paths(files)
    md = default_metadata(title, creators, description, tags)
    sums = build_checksums(files)
    log.info(f"Checksums: {json.dumps(sums, indent=2)}")

    results = {"internet_archive": None, "zenodo": None, "zenodo_doi": None}

    if dry_run:
        log.info("[DRY RUN] Skipping uploads.")
        return results

    if do_ia:
        if not identifier:
            # IA requires a unique identifier; derive one
            stem = title.lower().strip().replace(" ", "-")
            identifier = f"{stem}-{int(time.time())}"
        results["internet_archive"] = upload_to_internet_archive(
            identifier=identifier,
            files=files,
            md=md,
            collection=os.getenv("IA_COLLECTION"),
            mediatype=os.getenv("IA_MEDIATYPE", "texts"),
        )

    if do_zenodo:
        url, doi = upload_to_zenodo(
            files=files,
            md=md,
            publish=zenodo_publish,
            use_sandbox=zenodo_sandbox,
        )
        results["zenodo"] = url
        results["zenodo_doi"] = doi

    return results
