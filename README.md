# Shopping

A local grocery-planning assistant for Codex. Start with the meals you want to cook and the food you already have. Shopping calculates what to buy, matches the list to products at your store, and prepares a cart you can review before checkout.

**Provigo** is the first supported store, through an unofficial PC Express integration. The meal planner also works without a retailer account.

## Try it in Codex

Open this repository in Codex. For a first run, ask “Plan four dinners for next week. Ask what I already have, then work out what I need to buy.” You can also invoke a project skill directly.

| Skill | What you get |
| --- | --- |
| [`shopping-profile`](.agents/skills/shopping-profile/SKILL.md) | A private profile of food preferences, dietary constraints, and shopping habits. |
| [`plan-week`](.agents/skills/plan-week/SKILL.md) | A meal plan and ingredient quantities that account for batch sizes, leftovers, and pantry stock. |
| [`shop`](.agents/skills/shop/SKILL.md) | A verified account cart with package sizes, quantities, line prices, and a subtotal. |
| [`generate-cart-pdf`](.agents/skills/generate-cart-pdf/SKILL.md) | A shareable PDF grouped by meal. Shared ingredients are split across dishes, and household items appear under **General**. |

## Quick start

The dependency lock was verified with CPython 3.14 on macOS with Apple silicon. Run the following commands in a terminal with Git and that version of Python installed.

```sh
git clone --recurse-submodules https://github.com/FarnoodF/Shopping.git
cd Shopping
python3.14 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements.lock
git config --local core.hooksPath .githooks
.venv/bin/python -I scripts/shop.py init
.venv/bin/python -I scripts/shop.py status
```

The status command reports whether the private profile and retailer login are configured. You can start planning meals before signing in. The source supports Python 3.10 and later. Other Python versions and platforms need their own reviewed wheel hashes. PDF generation uses Pillow and ReportLab, which are available in the Codex workspace runtime.

## Connect a Provigo cart

The project uses a local Model Context Protocol (MCP) server to search products, read the account cart, and update quantities. Sign in to PC ID and verify the store and fulfillment method before the first cart update. Each shop ends with a fresh cart read, an itemized table, a PDF, and a link for the shopper to review. Checkout is a separate step. See the [connection guide](docs/provigo-api.md) and [cart procedure](docs/shopping-procedure.md).

The integration uses an undocumented retailer API. Product-detail requests returned HTTP 400 in the recorded live checks. The store guide explains when to use the product page to verify a label or package size. See the [Provigo reference](.agents/skills/shop/references/provigo.md).

## Privacy and development

Profiles, credentials, meal plans, cart snapshots, and generated PDFs are stored under `.profile/`. Git ignores that directory, and the local commit hook checks staged paths for private files. The directory is unencrypted. Keep it out of shared folders, and review a cart PDF before sharing it.

- [Contributing](CONTRIBUTING.md) covers local tests, synthetic fixtures, and the requirements for retailer changes.
- [Security reporting](SECURITY.md) explains how to report a vulnerability privately.
- [Integration security review](docs/security-review.md) documents the scope and limitations of the pinned upstream code.
