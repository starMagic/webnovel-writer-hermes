#!/usr/bin/env python3
"""
Generate manifest.json for the webnovel-writer .opencode/ directory.
Lists every file with SHA256 hash and size. Used for incremental updates.

Usage:
  python .opencode/scripts/gen_manifest.py [--version v1.2.0] > manifest.json
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def hash_file(path: Path) -> str:
    """Compute SHA256 hex digest of a file."""
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def build_manifest(opencode_dir: Path, version: str,
                   tag: str = "", updated: str = "",
                   changelog: list = None) -> dict:
    """Build manifest dict for all files under opencode_dir."""
    files = {}
    for root, dirs, filenames in os.walk(opencode_dir):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', 'node_modules', '.git')]
        for fn in filenames:
            if fn.endswith('.pyc'):
                continue
            full = Path(root) / fn
            rel = full.relative_to(opencode_dir.parent).as_posix()
            st = full.stat()
            files[rel] = {
                "sha256": hash_file(full),
                "size": st.st_size,
            }

    return {
        "version": version,
        "tag": tag,
        "updated": updated,
        "changelog": changelog or [],
        "files": files,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate manifest.json for webnovel-writer")
    parser.add_argument("--version", default="0.0.0")
    parser.add_argument("--tag", default="")
    parser.add_argument("--updated", default="")
    parser.add_argument("--changelog-file", default="",
                        help="Path to JSON file with changelog array")
    parser.add_argument("--opencode-dir", default=".opencode")
    args = parser.parse_args()

    changelog = []
    if args.changelog_file and Path(args.changelog_file).is_file():
        changelog = json.loads(Path(args.changelog_file).read_text(encoding="utf-8"))

    opencode_dir = Path(args.opencode_dir).resolve()
    if not opencode_dir.is_dir():
        print(f"Error: {opencode_dir} not found", file=sys.stderr)
        sys.exit(1)

    manifest = build_manifest(opencode_dir, args.version,
                              tag=args.tag, updated=args.updated,
                              changelog=changelog)
    # ensure_ascii=True avoids encoding issues with non-UTF-8 filesystem paths
    # (e.g., GBK-encoded Chinese paths on Windows that break Linux CI runners)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
