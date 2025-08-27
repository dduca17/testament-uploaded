#!/usr/bin/env python3
# MIT License
import argparse, sys, json
from uploader_core import run_archive

def parse_args():
    p = argparse.ArgumentParser(
        description="The Testament Uploader — CLI (IA + Zenodo)"
    )
    p.add_argument("--title", required=True, help="Work title")
    p.add_argument("--creator", action="append", default=[], help="Creator name (repeatable)")
    p.add_argument("--description", required=True, help="Long description")
    p.add_argument("--tag", action="append", default=[], help="Keyword tag (repeatable)")
    p.add_argument("--file", action="append", required=True, help="File to include (repeatable)")
    p.add_argument("--identifier", help="Internet Archive identifier (auto if omitted)")
    p.add_argument("--no-ia", action="store_true", help="Skip Internet Archive upload")
    p.add_argument("--no-zenodo", action="store_true", help="Skip Zenodo upload")
    p.add_argument("--zenodo-no-publish", action="store_true", help="Create deposition but do not publish")
    p.add_argument("--zenodo-live", action="store_true", help="Use live Zenodo (not sandbox)")
    p.add_argument("--dry-run", action="store_true", help="Do everything except actual upload")
    return p.parse_args()

def main():
    a = parse_args()
    res = run_archive(
        title=a.title,
        creators=a.creator,
        description=a.description,
        tags=a.tag,
        files=a.file,
        identifier=a.identifier,
        do_ia=not a.no_ia,
        do_zenodo=not a.no_zenodo,
        zenodo_publish=not a.zenodo_no_publish,
        zenodo_sandbox=not a.zenodo_live,
        dry_run=a.dry_run
    )
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    sys.exit(main() or 0)
