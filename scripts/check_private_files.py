#!/usr/bin/env python3
"""Reject private files in Git's index, including files force-added past .gitignore."""
from pathlib import PurePosixPath
import subprocess
import sys

result = subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True)
blocked = []
for raw in result.stdout.split(b"\0"):
    if not raw:
        continue
    path = PurePosixPath(raw.decode())
    name = path.name
    if (".profile" in path.parts or name == ".env" or
        (name.startswith(".env.") and name != ".env.example") or
        name.endswith(".har") or name in ("pcid_token_state.json", "redirect.txt", "pending.json")):
        blocked.append(str(path))
if blocked:
    print("Private files must not be version controlled:\n" + "\n".join(blocked), file=sys.stderr)
    sys.exit(1)
print("Git privacy check passed.")
