# Provigo

## Connect and verify the store

Before the first connection, read the [security review](../../../../docs/security-review.md) and [Provigo API guide](../../../../docs/provigo-api.md). Use the reviewed local stdio MCP server. Keep the upstream submodule pinned and verify its hashes before import. Changes to upstream source or dependencies require a fresh review. Avoid the upstream setup wizard, automated login, HTTP server, Docker image and deployment workflows.

Load the private connection settings and run `.venv/bin/python -I scripts/shop.py status` from the repository root. When API authentication is needed, follow the [private login procedure](../../../../docs/provigo-api.md#private-login-procedure). Website and API sign-in are separate. Keep tokens and redirects under `.profile/auth/`.

Use the connected Provigo MCP tools for searches, product details, cart reads and quantity updates. When they are unavailable in chat, call the same server with `.venv/bin/python -I scripts/mcp_call.py`. Follow the API guide for arguments and private output paths. Run the live read checks before the first write, verify the Provigo banner, store ID and fulfillment method, and save evidence under `.profile/`.

## Fill the account cart

1. Read the baseline with `view_cart`. If it reports no open cart or an anonymous customer, add one unit of a planned grocery in the signed-in app or website. Confirm its code and quantity with `view_cart` before filling the rest, and count that unit toward the target. Follow [Opening an account cart](../../../../docs/shopping-procedure.md#opening-an-account-cart).
2. Use `set_quantity` for the **absolute** target quantity. Verify the first needed item through MCP before proceeding. Read back each change. After two equivalent unexplained failures, stop the failing writes, preserve progress privately and use the signed-in fallback or report the specific blocker.
3. After the last change, read the whole cart with `view_cart` and reconcile all lines and the subtotal. A successful MCP readback is sufficient. Report line prices in CAD and provide the [Provigo cart review link](https://www.provigo.ca/en/cart).

Use computer use only for interactive login or a specific unsupported or failed capability. For example, the documented product-detail request returned HTTP 400. Check the product page if the label or average weight is missing from search and cart results. Record the actual limitation, respect access controls and return to MCP for supported operations. Follow the [basket procedure](../../../../docs/shopping-procedure.md) for browser fallback and the private basket record.
