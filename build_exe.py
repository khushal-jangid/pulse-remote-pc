"""
Pulse Remote v2.0 - Standalone Windows Executable (.exe) Builder
Packages the entire Python PC Agent, dependencies, and static web client into a single .exe.
"""
import os
import sys
import dis
import shutil
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Fix Python 3.10.0 dis module bug (bpo-45434 / IndexError on extended constants)
orig_get_const_info = dis._get_const_info
def safe_get_const_info(const_index, const_list):
    argval = const_index
    if const_list is not None and 0 <= const_index < len(const_list):
        argval = const_list[const_index]
    return argval, repr(argval)
dis._get_const_info = safe_get_const_info

orig_get_name_info = dis._get_name_info
def safe_get_name_info(name_index, name_list):
    argval = name_index
    if name_list is not None and 0 <= name_index < len(name_list):
        argval = name_list[name_index]
        argrepr = argval
    else:
        argrepr = repr(argval)
    return argval, argrepr
dis._get_name_info = safe_get_name_info

def build():
    base_dir = Path(__file__).resolve().parent
    static_dir = base_dir / "static"
    dist_dir = base_dir / "dist"
    build_dir = base_dir / "build"
    output_exe = dist_dir / "PulseRemote.exe"
    desktop_exe = base_dir / "PulseRemote.exe"

    os.chdir(str(base_dir))

    print("=" * 65)
    print("  ⚡ PULSE REMOTE - STANDALONE WINDOWS EXE BUILDER")
    print("=" * 65)
    print(f"> Project Directory: {base_dir}")
    print(f"> Static Assets:     {static_dir}")
    print(f"> Target Output:     {output_exe}")
    print("=" * 65)

    pyi_args = [
        "--noconfirm",
        "--onefile",
        "--console",
        "--name", "PulseRemote",
        "--add-data", f"{static_dir};static",
        "--hidden-import", "aiohttp",
        "--hidden-import", "websockets",
        "--hidden-import", "mss",
        "--hidden-import", "cv2",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageTk",
        "--hidden-import", "pyautogui",
        "--hidden-import", "psutil",
        "--hidden-import", "qrcode",
        "--hidden-import", "tkinter",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--specpath", str(base_dir),
        str(base_dir / "agent.py"),
    ]

    print("[1/3] Compiling and bundling Python environment via PyInstaller...")
    import PyInstaller.__main__
    try:
        PyInstaller.__main__.run(pyi_args)
    except SystemExit as e:
        if e.code != 0:
            print(f"\n❌ Build failed with exit code: {e.code}")
            return False
    except Exception as e:
        print(f"\n❌ Build error: {e}")
        return False

    if output_exe.exists():
        print("\n[2/3] Build succeeded!")
        shutil.copy2(output_exe, desktop_exe)
        size_mb = desktop_exe.stat().st_size / (1024 * 1024)
        print(f"[3/3] Ready! Single-file executable created at:")
        print(f"      📍 {desktop_exe} ({size_mb:.2f} MB)")
        print("\n✅ Anyone can now download and run 'PulseRemote.exe' directly without installing Python!")
        return True
    else:
        print("\n❌ Executable not found at expected location:", output_exe)
        return False

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
