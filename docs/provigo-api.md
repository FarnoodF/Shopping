# Provigo integration research

Researched on 2026-11-01. No documented public consumer-basket developer program was found in searches of Provigo, PC Express, Loblaw, and Loblaw Digital. This is a search finding, not proof that a private partner API does not exist. Plugin discovery did not return a relevant Provigo/PC Express integration.

- [Provigo shopping site](https://www.provigo.ca/en): consumer shopping and basket interface.
- [Loblaw supplier portal support](https://www.loblaw.ca/en/supplier-portal-support/): supplier accounts, catalog/workflow/reporting support; not consumer cart developer access.
- [PC Express](https://www.pcexpress.ca/): consumer grocery service.
- [Unofficial PC Express MCP project](https://github.com/FireBall1725/pcexpress-mcp-server): upstream describes an undocumented API and app OAuth flow recovered through reverse engineering.

The upstream clone is a Git submodule at `vendor/pcexpress-mcp-server`, pinned to `1b131c91bdcabeaee317c70e937592878d201668`. Its AGPL-3.0 license and attribution remain intact. Use its source through `shopping_agent.retailer`, not its deployment scripts. See [security-review.md](security-review.md) for reviewed scope, findings, mitigations, and remaining limitations.

## Local connection

The preferred shopping interface is the local MCP server, launched by `scripts/shop.py mcp`. It exposes `search_products`, `product_details`, `view_cart`, and `set_quantity` over stdio. It uses a restricted subclass of the upstream `PCExpressAPI` and `TokenManager`, adds `provigo` explicitly instead of falling back to Zehrs, keeps authentication in `.profile/auth`, blocks non-retailer destinations and checkout routes, and has no HTTP listener. The CLI remains useful for setup/authentication and diagnostics.

When these tools are not connected directly to the chat, `scripts/mcp_call.py` starts the reviewed stdio server, initializes a real MCP client session, and calls one named tool. It reads the argument object from stdin and saves the tool result privately under `.profile/`. It never automatically retries mutations. This is an MCP call, not a direct retailer-client shortcut, and requires no global client configuration.

```sh
.venv/bin/python -I scripts/mcp_call.py view_cart <<'JSON'
{}
JSON
.venv/bin/python -I scripts/mcp_call.py search_products --output search-result.json <<'JSON'
{"query":"ingredient name"}
JSON
```

`--output` accepts a JSON path relative to `.profile` and rejects absolute paths, traversal and symlinks. For `set_quantity`, send `product_code`, integer `quantity`, `fulfillment` (`pickup` or `delivery`), and the prepared `week` (`YYYY-MM-DD`). Read with `view_cart` before and after a write. The saved MCP result contains `structuredContent` when supplied, otherwise JSON text in a `content` block; check `isError` before using it. Keep raw account/cart results out of tracked files.

Live checks on 2026-11-01 succeeded for PC ID login, customer lookup, store lookup, product search, reading an authenticated cart, and setting product quantities with readback. Prices and availability depend on the actual selected store. The upstream source omits Provigo; the local banner mapping was exercised in these checks.

The upstream `GET /products/{code}` detail request returned HTTP 400, including a read-only trial with the known store/language/banner context. Do not keep replaying that request or claim the detail command is working. MCP search/cart results still provide product codes, brands, package/price information and availability. Use the website only when necessary details such as labels or average weights remain unavailable through MCP. Product-detail support remains a limitation. Successful MCP readback does not require a browser check.

Account authentication, browser sign-in and open-cart discovery are separate. Live searches succeeded with valid API credentials while `view_cart` reported no open Provigo cart. Adding products in a signed-out browser populated a guest basket. The account read still found no open cart. Adding one planned grocery in the signed-in app made the account cart discoverable and quantity updates succeeded. An empty profile-linked cart can also report an anonymous customer. For either condition, follow [Opening an account cart](shopping-procedure.md#opening-an-account-cart).

## Private login procedure

1. Run `.venv/bin/python -I scripts/shop.py login-start`. It saves a short-lived PKCE verifier/state privately and returns an authorization URL on `accounts.pcid.ca`. Open it through the available browser/computer-use tool. Do not use upstream automated-login or credential-extraction scripts.
2. The user signs into PC ID in their normal browser. If the provider requests consent to ongoing account access, obtain any action-time confirmation required by the active browser tool. This API flow requests `offline_access` to refresh the login; do not silently treat the existing website session as that consent.
3. After login, save the complete `com.loblaw.pcx://pcx-android/login/appredirect?...` response in `.profile/auth/redirect.txt` using a private local editor (mode 600). Do not paste it into chat or shell arguments. The browser may show an error for the app-specific URL; stop if it instead shows a security warning or actual login error. Do not extract browser cookies or inspect browser credential stores.
4. Run `.venv/bin/python -I scripts/shop.py login-finish` within 15 minutes. It rejects missing/mismatched state, exchanges the code only with PC ID, saves the rotated credentials locally, and deletes consumed temporary login files. It prints no token. Authentication must be resumed if the provider's response format differs; do not weaken validation to force success.
5. Run `customer` to retrieve the home-store hint without dumping personal details. Verify the store using `store FOUR_DIGIT_ID` and the store shown on the website. Save the verified ID, name, and fulfillment in `.profile/connection.json`; never use a placeholder for a real shop.
6. Run the customer, store, product search and cart read checks and record the results privately. If the cart read reports no open cart or an anonymous customer, use the signed-in first-item procedure above.

Only one process may use the token chain at a time; the adapter enforces a local file lock. No background daemon or scheduled job is installed. Re-login if a token is revoked; do not repeatedly consume a failing refresh token.

## Commands

```sh
.venv/bin/python -I scripts/shop.py status
.venv/bin/python -I scripts/shop.py search "ingredient name"
.venv/bin/python -I scripts/shop.py product PRODUCT_CODE
.venv/bin/python -I scripts/shop.py cart
.venv/bin/python -I scripts/shop.py set-quantity PRODUCT_CODE 1 --fulfillment pickup --week YYYY-MM-DD
.venv/bin/python -I scripts/shop.py mcp
```

The quantity command is a real basket mutation. Invoke only for the user's prepared shopping list; inspect the cart afterward. Both entrypoints require recorded dietary restrictions and a complete weekly plan before mutation. They do not place orders.

For an MCP client, configure the absolute path to this checkout's `.venv/bin/python`, arguments `-I`, the absolute path to `scripts/shop.py`, and `mcp`. Keep machine-specific client configuration under `.profile/`; never put a refresh token in that configuration. This project does not change global Codex settings.

If the undocumented API is incompatible or blocked, use the website procedure in [shopping-procedure.md](shopping-procedure.md). Do not retry guessed routes or bypass a CAPTCHA/access restriction.
