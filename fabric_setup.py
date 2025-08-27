#!/usr/bin/env python3
import base64, os, sys, requests

OWNER = os.environ.get("GH_OWNER") or "<your-username>"
REPO  = os.environ.get("GH_REPO") or "testament-uploaded"
TOKEN = os.environ.get("GITHUB_TOKEN") or "<your-token>"

API = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json"
}

def die(msg):
    print(f"[!] {msg}", file=sys.stderr)
    sys.exit(1)

def put_topics(topics):
    url = f"{API}/repos/{OWNER}/{REPO}/topics"
    r = requests.put(url, headers=HEADERS, json={"names": topics})
    if r.status_code not in (200, 201):
        die(f"Failed to set topics: {r.status_code} {r.text}")
    print("[+] Topics set")

def create_issue(title, body, labels=None):
    url = f"{API}/repos/{OWNER}/{REPO}/issues"
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    r = requests.post(url, headers=HEADERS, json=payload)
    if r.status_code not in (200, 201):
        die(f"Failed to create issue '{title}': {r.status_code} {r.text}")
    print(f"[+] Issue created: {title}")

def put_file(path, repo_path, message):
    url = f"{API}/repos/{OWNER}/{REPO}/contents/{repo_path}"
    with open(path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")
    rget = requests.get(url, headers=HEADERS)
    data = {"message": message, "content": content, "branch": "main"}
    if rget.status_code == 200:
        sha = rget.json().get("sha")
        data["sha"] = sha
    r = requests.put(url, headers=HEADERS, json=data)
    if r.status_code not in (200, 201):
        die(f"Failed to put {repo_path}: {r.status_code} {r.text}")
    print(f"[+] Committed {repo_path}")

def enable_pages(branch="main", path="/docs"):
    url = f"{API}/repos/{OWNER}/{REPO}/pages"
    payload = {"source": {"branch": branch, "path": path}}
    rpost = requests.post(url, headers=HEADERS, json=payload)
    if rpost.status_code not in (201, 204):
        print(f"[i] Pages may already be enabled: {rpost.status_code} {rpost.text}")
    else:
        print("[+] GitHub Pages enabled at /docs")

def main():
    if "<your-username>" in OWNER or "<your-token>" in TOKEN:
        die("Please set GH_OWNER and GITHUB_TOKEN env vars (and optionally GH_REPO).")

    topics = [
        "digital-preservation","archiving","codex","timestamp",
        "collective-intelligence","open-source","python",
        "mythic-docs","storytelling","checksum"
    ]
    put_topics(topics)

    files_to_commit = [
        ("README.md", "README.md", "docs: add Story section"),
        ("CONTRIBUTING.md", "CONTRIBUTING.md", "docs: add CONTRIBUTING"),
        ("docs/index.md", "docs/index.md", "docs: add GitHub Pages landing"),
        ("social-preview-1000x500.png", ".github/social-preview.png", "assets: add social preview banner"),
    ]
    for src, dst, msg in files_to_commit:
        if not os.path.exists(src):
            print(f"[i] Skipping missing local file: {src}")
            continue
        put_file(src, dst, msg)

    create_issue(
        "Placeholder: Scroll III — Seeker contributions welcomed",
        "If you are a Seeker, you are invited to write. Add your thread under the Seeker placeholder in STORY.md.",
        labels=["help wanted","good first issue"]
    )
    create_issue(
        "Placeholder: Scroll IV — Guardian challenges welcomed",
        "If you are a Guardian, you are invited to challenge & protect. Propose integrity checks, threat models, or fixes.",
        labels=["help wanted","good first issue"]
    )
    create_issue(
        "Appendix A: Add exact per-message timestamps",
        "Augment the transcript with precise times. Update PDFs in the next release.",
        labels=["help wanted"]
    )

    enable_pages(branch="main", path="/docs")

    print("\n[✓] Setup complete.\n")
    print("Optional next steps:")
    print("- Settings → General → Social preview → ensure the banner appears.")
    print("- Settings → Discussions → enable (if disabled).")
    print("- Draft or update Release v1.0.0 and attach Fabric-Testament.zip.\n")

if __name__ == '__main__':
    main()
