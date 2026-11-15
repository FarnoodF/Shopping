# Contributing

Open a pull request against `main`. Describe the change from the shopper’s perspective and include the checks you ran. For security issues, use [private vulnerability reporting](SECURITY.md).

## Run the checks

Complete the [development environment setup](README.md#quick-start), then install the test tools separately from the locked runtime dependencies.

```sh
.venv/bin/python -m pip install pytest pytest-socket
.venv/bin/python -m pytest -q
python3 scripts/check_private_files.py
```

The test suite blocks network sockets. Use synthetic ingredients, dates, prices, and identifiers in tests and issue reports. Keep grocery receipts, account details, cart links with identifiers, and screenshots from a signed-in session in your private workspace.

## Where to make a change

| Change | Location |
| --- | --- |
| Meal coverage, portions, and ingredient arithmetic | [Planner](src/shopping_agent/planner.py) and [planner tests](tests/test_planner.py) |
| Shopping instructions and retailer-specific procedures | [Shop skill](.agents/skills/shop/SKILL.md) and its store references |
| Retailer requests or account-cart updates | [Retailer adapter](src/shopping_agent/retailer.py) and [MCP server](src/shopping_agent/mcp_server.py) |
| Meal-grouped PDFs | [PDF skill and renderer](.agents/skills/generate-cart-pdf/) |

Changes to the PC Express dependency or the locked runtime wheels require a fresh review. Document general findings in `docs/` and keep raw audit output in `.profile/audit/`. Distinguish offline tests from any authorized live checks when reporting results. See the [upstream review](docs/security-review.md).
