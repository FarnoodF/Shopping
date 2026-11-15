#!/usr/bin/env python3
"""Call the project's reviewed MCP server when no connected tool is exposed."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shopping_agent.private import PROFILE, ROOT, initialize, write_json

TOOLS = ("search_products", "product_details", "view_cart", "set_quantity")


def private_output(relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.name or path.suffix != ".json":
        raise ValueError("Output must be a JSON path relative to .profile")
    target = PROFILE / path
    if any(part.is_symlink() for part in (target, *target.parents)):
        raise ValueError("Private output paths must not contain symlinks")
    return target


async def call(tool, arguments):
    server = StdioServerParameters(
        command=str(ROOT / ".venv/bin/python"),
        args=["-I", str(ROOT / "scripts/shop.py"), "mcp"],
        cwd=str(ROOT),
    )
    # Runtime diagnostics can contain account context; keep them private.
    log = PROFILE / "audit/mcp-client.log"
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a") as errlog:
        async with stdio_client(server, errlog=errlog) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments, read_timeout_seconds=timedelta(seconds=90))
                return result.model_dump(mode="json", exclude_none=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=TOOLS)
    parser.add_argument("--output", default="mcp-last-result.json", help="JSON path relative to .profile")
    args = parser.parse_args()
    os.umask(0o077)
    initialize()
    target = private_output(args.output)
    raw = sys.stdin.read()
    arguments = json.loads(raw) if raw.strip() else {}
    if not isinstance(arguments, dict):
        raise ValueError("MCP arguments must be a JSON object")
    result = asyncio.run(call(args.tool, arguments))
    write_json(target, result)
    print(json.dumps({"tool": args.tool, "is_error": bool(result.get("isError")), "saved_to": str(target)}))
    return 1 if result.get("isError") else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print("MCP call did not complete. Inspect the private state before retrying; no mutation was automatically replayed.", file=sys.stderr)
        raise SystemExit(1)
