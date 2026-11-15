"""Local-only storage shared by the planner and retailer adapter."""
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / ".profile"


def private_dir(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError("Private directories must not be symlinks")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def write_json(path: Path, data) -> None:
    private_dir(path.parent)
    if path.is_symlink():
        raise ValueError("Private files must not be symlinks")
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path: Path):
    return json.loads(path.read_text())


def initialize() -> None:
    private_dir(PROFILE)
    for folder in ("auth", "weeks", "audit"):
        private_dir(PROFILE / folder)
    for name in ("preferences", "connection"):
        target = PROFILE / f"{name}.json"
        if not target.exists():
            write_json(target, read_json(ROOT / "config" / f"{name}.template.json"))
