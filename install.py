#!/usr/bin/env python3
"""
Webnovel Writer for Hermes — Installer
Usage:
  python install.py              # Install dependencies + register skills
  python install.py --uninstall  # Remove skills from Hermes
"""
import os, sys, shutil
from pathlib import Path

HERMES_SKILLS = Path.home() / ".hermes" / "skills" / "webnovel-writer-hermes"
REPO_ROOT = Path(__file__).resolve().parent

def install():
    print("Webnovel Writer for Hermes — Installer\n")
    
    # 1. Install Python dependencies
    print("[1/3] Installing Python dependencies...")
    req_file = REPO_ROOT / "requirements.txt"
    if req_file.exists():
        os.system(f"{sys.executable} -m pip install -r {req_file} -q")
    
    # 2. Register skills with Hermes
    print("[2/3] Registering skills...")
    skills_src = REPO_ROOT / ".hermes-skills"
    if skills_src.is_dir():
        if HERMES_SKILLS.exists():
            shutil.rmtree(HERMES_SKILLS)
        shutil.copytree(skills_src, HERMES_SKILLS)
        print(f"  ✓ {len(list(skills_src.iterdir()))} skills installed to {HERMES_SKILLS}")
    
    # 3. Verify
    print("[3/3] Verifying...")
    webnovel_py = REPO_ROOT / "scripts" / "webnovel.py"
    if webnovel_py.exists():
        result = os.popen(f"{sys.executable} {webnovel_py} --help 2>&1").read()
        if "usage:" in result.lower() or "命令" in result:
            print("  ✓ CLI entry point OK")
        else:
            print(f"  ⚠ CLI entry point may have issues: {result[:100]}")
    
    print(f"\nDone! Skills: {HERMES_SKILLS}")
    print("Usage in Hermes: skill_view(name='webnovel-write')")

def uninstall():
    print("Uninstalling Webnovel Writer skills from Hermes...")
    if HERMES_SKILLS.exists():
        shutil.rmtree(HERMES_SKILLS)
        print(f"  ✓ Removed {HERMES_SKILLS}")

if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install()
