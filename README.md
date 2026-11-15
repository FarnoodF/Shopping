# Shopping

A local grocery agent for learning preferences, planning a week of meals, and preparing a Provigo basket. Personal information stays in the Git-ignored `.profile/` directory. General skills, code, procedures, and the reviewed upstream dependency are version controlled.

## Use in this project

Ask the agent to **learn my shopping preferences**, **plan this week's meals**, **fill my Provigo basket**, or **generate my cart PDF by meal**. The [shop skill](.agents/skills/shop/SKILL.md) lists supported stores and links to each store’s integration instructions. Provigo is the first supported store. The [generate-cart-pdf skill](.agents/skills/generate-cart-pdf/SKILL.md) exports the verified basket.

The first run follows this order:

1. Learn household, tastes, eating/cooking patterns, and shopping habits.
2. Ask which meals to make for explicit dates and what food is already available.
3. Calculate portions and ingredients, subtract pantry stock, and fill the basket.

Basket preparation stops before order submission. Setup runs locally without installing a recurring automation, background service, or global MCP connection.

## Structure

```text
.agents/skills/       reusable preference, planning, and shopping skills
src/shopping_agent/   private storage, quantity planner, reviewed retailer adapter
scripts/             local command entrypoint and Git privacy check
config/              blank templates and upstream source fingerprints
docs/                research, security review, interview and shopping procedures
tests/               quantity, credential, request-boundary, and privacy checks
vendor/              pinned unofficial PC Express Git submodule
.profile/            PRIVATE: preferences, credentials, weekly plans and run records
```

## Setup and verification

Set up a new checkout on the audited platform (CPython 3.14, macOS arm64) with the following commands.

```sh
git submodule update --init
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements.lock
.venv/bin/python -I scripts/shop.py init
git config core.hooksPath .githooks
```

The lock contains the exact 32 runtime distributions and downloaded wheel hashes. On another Python/platform, re-resolve upstream requirements from PyPI in a fresh environment, audit the new resolution, and replace the lock after review. Do not silently drop hashes. The source itself uses Python 3.10+.

Developer tools are separate from the runtime lock:

```sh
.venv/bin/python -m pip install pytest pytest-socket bandit pip-audit
.venv/bin/python -m pytest -q
.venv/bin/python -m pip_audit -r requirements.lock --no-deps --disable-pip
python3 scripts/check_private_files.py
```

Tests disable network sockets. On macOS, tests were also run under `sandbox-exec` with network access denied. The test data is synthetic; tests do not authenticate or modify a real basket.

## Integration status

The unofficial project is cloned at commit `1b131c91bdcabeaee317c70e937592878d201668`. Review found no obvious malware/backdoor in the inspected source, but identified security issues in the stock deployment/login paths. This project uses a local wrapper addressing those paths. See [the security review](docs/security-review.md) and [connection procedure](docs/provigo-api.md).

Live authentication, search, store/cart reads and basket quantity updates have succeeded. Product details remain limited by an HTTP 400 response; use browser details only where needed. Prefer the local MCP tools for shopping, using `scripts/mcp_call.py` if the chat does not expose them directly. See the connection procedure for examples. Every completed basket update includes an item/brand/amount/line-price table and total. Personal observations are saved only in `.profile/`.

`.profile` is excluded from Git and guarded against accidental force-adding by a local commit hook. It is not encrypted, and Git ignore rules do not control independent device/cloud backups. Keep it out of any separate sync configuration.
