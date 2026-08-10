#!/usr/bin/env python3
"""
PulseRemote PC - 1-Click Release & Update Publisher
Automates rebuilding binaries, packaging installer, committing git tags, updating GitHub Pages website, and uploading GitHub Releases.
"""

import os
import sys
import subprocess
import zipfile
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop", "PulseRemote-Setup-v1.0.exe")
if not os.path.exists(os.path.dirname(DESKTOP_PATH)):
    DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "PulseRemote-Setup-v1.0.exe")

def run_cmd(cmd, cwd=BASE_DIR):
    print(f"\n🚀 Running: {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd)
    if res.returncode != 0:
        print(f"❌ Error executing command: {cmd}")
        sys.exit(1)

def main():
    print("=" * 65)
    print(" 📱 PulseRemote PC — 1-Click Update Publisher & Release Tool ")
    print("=" * 65)

    ver = input("\n📌 Enter New Version Tag (e.g., v1.1.0 or v1.0.1): ").strip()
    if not ver:
        print("❌ Version tag cannot be empty!")
        return

    if not ver.startswith("v"):
        ver = "v" + ver

    notes = input("📝 Enter Short Release Notes / Changelog: ").strip()
    if not notes:
        notes = f"Release update {ver} for PulseRemote PC"

    confirm = input(f"\n⚠️ Confirm publishing version '{ver}'? (Y/n): ").strip().lower()
    if confirm not in ['y', 'yes', '']:
        print("Cancelled.")
        return

    print("\n-------------------------------------------------------------")
    print("Step 1/5: Building PyInstaller Standalone Distribution...")
    print("-------------------------------------------------------------")
    pyinst_cmd = (
        'python -m PyInstaller --noconfirm --onedir --windowed --name "PulseRemote" '
        '--add-data "public;public" --add-data "bin;bin" --add-data "node_modules;node_modules" '
        '--add-data "server.js;." --add-data "ps-bridge.js;." --add-data "py-worker.py;." pulse_app.py'
    )
    run_cmd(pyinst_cmd)

    print("\n-------------------------------------------------------------")
    print("Step 2/5: Creating Compressed Application Payload Archive...")
    print("-------------------------------------------------------------")
    dist_dir = os.path.join(BASE_DIR, 'dist', 'PulseRemote')
    zip_path = os.path.join(BASE_DIR, 'app_payload.zip')

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dist_dir):
            for file in files:
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, dist_dir)
                zipf.write(full_p, rel_p)

    payload_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2)
    print(f"✔ app_payload.zip created ({payload_mb} MB)")

    print("\n-------------------------------------------------------------")
    print("Step 3/5: Compiling Single-File Setup Wizard Installer (.exe)...")
    print("-------------------------------------------------------------")
    wiz_cmd = (
        'python -m PyInstaller --noconfirm --onefile --windowed --name "PulseRemote-Setup-v1.0" '
        '--add-data "app_payload.zip;." installer_wizard.py'
    )
    run_cmd(wiz_cmd)

    exe_dist = os.path.join(BASE_DIR, 'dist', 'PulseRemote-Setup-v1.0.exe')
    if os.path.exists(exe_dist):
        try:
            shutil.copy2(exe_dist, DESKTOP_PATH)
            print(f"✔ Copied setup installer to Desktop: {DESKTOP_PATH}")
        except Exception as e:
            print(f"⚠️ Could not copy to Desktop: {e}")

    print("\n-------------------------------------------------------------")
    print("Step 4/5: Updating GitHub Pages Docs & Pushing Git Code...")
    print("-------------------------------------------------------------")
    docs_dir = os.path.join(BASE_DIR, 'docs')
    web_dir = os.path.join(BASE_DIR, 'web-landing')

    if os.path.exists(web_dir):
        if os.path.exists(docs_dir):
            shutil.rmtree(docs_dir)
        shutil.copytree(web_dir, docs_dir)
        print("✔ Synced web-landing to docs folder")

    run_cmd('git add .')
    run_cmd(f'git commit -m "Release {ver}: {notes}"')
    run_cmd(f'git tag {ver}')
    run_cmd('git push origin master --tags')

    print("\n-------------------------------------------------------------")
    print("Step 5/5: Creating GitHub Release & Uploading Installer Executable...")
    print("-------------------------------------------------------------")
    gh_rel_cmd = f'gh release create {ver} "{exe_dist}" --title "PulseRemote PC {ver}" --notes "{notes}"'
    run_cmd(gh_rel_cmd)

    print("\n=============================================================")
    print(f" 🎉 RELEASE {ver} PUBLISHED SUCCESSFULLY!")
    print("=============================================================")
    print("🌐 Website URL:  https://khushal-jangid.github.io/pulse-remote-pc/")
    print(f"📦 Release URL:  https://github.com/khushal-jangid/pulse-remote-pc/releases/tag/{ver}")
    print("=============================================================\n")

if __name__ == '__main__':
    main()
