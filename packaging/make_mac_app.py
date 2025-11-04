"""Create a minimal macOS .app bundle for the GUI."""
from __future__ import annotations

import re
import shutil
import stat
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
APP_NAME = "Serato Rekordbox Sync.app"
CONTENTS = DIST_DIR / APP_NAME / "Contents"
MACOS = CONTENTS / "MacOS"
RESOURCES = CONTENTS / "Resources"
APP_RESOURCES = RESOURCES / "app"
EMBEDDED_PYTHON = RESOURCES / "python"


def _create_python_runtime() -> Path:
    """Bundle a standalone Python interpreter inside the app."""

    if EMBEDDED_PYTHON.exists():
        shutil.rmtree(EMBEDDED_PYTHON)

    builder = venv.EnvBuilder(with_pip=False, symlinks=False)
    builder.create(EMBEDDED_PYTHON)

    bin_dir = EMBEDDED_PYTHON / "bin"
    for name in ("python3", "python"):
        candidate = bin_dir / name
        if candidate.exists():
            return candidate

    # Fall back to python3.x style names created by some distributors.
    for candidate in sorted(bin_dir.glob("python3.*")):
        if candidate.is_file():
            return candidate

    raise SystemExit("Unable to locate the embedded python interpreter")


def _read_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"^version\s*=\s*\"([^\"]+)\"", text, re.MULTILINE)
    return match.group(1) if match else "0.0.0"


def _write_file(path: Path, content: str, *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def build_app() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if (DIST_DIR / APP_NAME).exists():
        shutil.rmtree(DIST_DIR / APP_NAME)

    package_src = ROOT / "src" / "serato_rekordbox_sync"
    if not package_src.exists():
        raise SystemExit("Could not find serato_rekordbox_sync package")

    APP_RESOURCES.mkdir(parents=True, exist_ok=True)
    shutil.copytree(package_src, APP_RESOURCES / "serato_rekordbox_sync")

    launcher = APP_RESOURCES / "launch.py"
    launcher_code = """
import pathlib
import runpy
import sys

APP_ROOT = pathlib.Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
runpy.run_module("serato_rekordbox_sync.gui", run_name="__main__")
""".strip()
    _write_file(launcher, launcher_code)

    python_executable = _create_python_runtime()

    executable = MACOS / "serato-rekordbox-sync"
    exec_script = """
#!/bin/bash
set -e
APP_DIR="$(cd \"$(dirname \"$0\")/..\" && pwd)"
APP_PY="$APP_DIR/Resources/app"
PYTHON_BIN="$APP_DIR/Resources/python/bin/PYTHON_BIN_PLACEHOLDER"
export PYTHONPATH="$APP_PY"
exec "$PYTHON_BIN" "$APP_PY/launch.py"
""".strip() + "\n"
    exec_script = exec_script.replace("PYTHON_BIN_PLACEHOLDER", python_executable.name)
    MACOS.mkdir(parents=True, exist_ok=True)
    _write_file(
        executable,
        exec_script,
        mode=stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
    )

    version = _read_version()
    info_plist = f"""
<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
    <key>CFBundleName</key>
    <string>Serato ↔︎ Rekordbox Sync</string>
    <key>CFBundleDisplayName</key>
    <string>Serato ↔︎ Rekordbox Sync</string>
    <key>CFBundleIdentifier</key>
    <string>com.openai.serato-rekordbox-sync</string>
    <key>CFBundleExecutable</key>
    <string>serato-rekordbox-sync</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{version}</string>
    <key>CFBundleVersion</key>
    <string>{version}</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
"""
    _write_file(CONTENTS / "Info.plist", info_plist)
    _write_file(CONTENTS / "PkgInfo", "APPL????")

    print(f"Built {APP_NAME} in {DIST_DIR}")


if __name__ == "__main__":
    build_app()
