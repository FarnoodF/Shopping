# Shopping agent

Use this repository to learn the user's preferences, plan a week of meals, and prepare a basket at the selected store. Follow the user's requested order and resume from `.profile/workflow.json` when present.

## Routing

- Learn or update lasting tastes, eating patterns, and shopping habits: read `.agents/skills/shopping-profile/SKILL.md`.
- Ask what to cook this week and produce quantities: read `.agents/skills/plan-week/SKILL.md`.
- To fill, update or show the current basket, use [shop](.agents/skills/shop/SKILL.md).
- To generate a shareable PDF grouped by meal from a verified basket, use [generate-cart-pdf](.agents/skills/generate-cart-pdf/SKILL.md).

These are project skills. Keep their instructions general; use the private profile for personal facts. They can be invoked by name in a chat working in this repository, even if a client has not refreshed its skill picker.

## Private information

All user answers, location/store choices, pantry inventories, meal plans, product selections, basket snapshots, receipts, tokens, screenshots, and run logs belong under `.profile/`. Never copy them into documentation, tests, commit messages, skills, or tracked examples. Do not put credentials in chat, command arguments, shell history, or a tracked MCP configuration. Keep authentication data in `.profile/auth/`; never request a password in chat. Use `shopping_agent.private.write_json` for private JSON writes.

`.gitignore` and the local commit hook exclude private files from Git. This is not encryption or a guarantee about independent computer backups. Do not upload `.profile` or configure syncing for it. No remote is needed for ordinary local use.

## Retailer integration

Read the selected retailer’s reference in the shop skill before connecting. It defines the reviewed tools, login procedure, first-write checks and supported fallback. Verify the signed-in account cart, preserve existing items and finish with the basket ready for user review. Order submission requires a separate request.

## Development

- The code requires Python 3.10+. The audited environment uses CPython 3.14.
- `requirements.lock` pins the exact audited runtime wheels for macOS arm64. See README for re-resolving on another platform.
- Run `python3 scripts/check_private_files.py` before committing.
- For runtime changes, run `.venv/bin/python -m pytest -q`. Tests block network sockets by default.
- Record only general findings in `docs/`; keep raw audit outputs in `.profile/audit/`.

## Completion evidence

Distinguish project setup, offline tests, live read tests, and verified basket writes. Never report a basket as complete from a successful request alone: reconcile the actual products, package sizes, quantities, unavailable items, and visible subtotal against the weekly list.

Whenever `shop` presents a verified cart, run `generate-cart-pdf` and deliver its PDF with the inline item/brand/amount/line-price table, total and cart review link. This includes requests to show an existing cart. Keep personal defaults in `.profile/` and general reporting and integration procedures in version control.
