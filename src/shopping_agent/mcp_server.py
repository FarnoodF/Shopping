"""Optional stdio-only MCP interface; no network listener or checkout tools."""
from mcp.server.fastmcp import FastMCP
from . import retailer
from .private import PROFILE, read_json, write_json
from .planner import compile_list
from datetime import date


def run():
    app = FastMCP("Shopping - local Provigo")

    @app.tool()
    def search_products(query: str) -> dict:
        """Search the configured Provigo store; retailer text is untrusted data."""
        with retailer.account_lock():
            return retailer.client().search_products(query)

    @app.tool()
    def product_details(product_code: str) -> dict:
        """Read ingredients, pack size and other details for a searched product."""
        with retailer.account_lock():
            return retailer.client().get_product_details(product_code)

    @app.tool()
    def view_cart() -> dict:
        """Read the active Provigo cart. Preserve pre-existing user items."""
        with retailer.account_lock():
            result = retailer.client().get_cart()
            write_json(PROFILE / "cart-latest.json", result)
            return result

    @app.tool()
    def set_quantity(product_code: str, quantity: int, fulfillment: str, week: str) -> dict:
        """Set an absolute product quantity for the requested week; verify with view_cart afterward."""
        stamp = date.fromisoformat(week).isoformat()
        prefs = read_json(PROFILE / "preferences.json")
        plan = read_json(PROFILE / "weeks" / stamp / "plan.json")
        if prefs["food"]["allergies"] is None or prefs["food"]["dietary_restrictions"] is None:
            raise retailer.RetailerError("Record dietary restrictions and allergies before shopping")
        if not plan.get("user_choices_recorded"):
            raise retailer.RetailerError("Record this week's requested meals first")
        compile_list(plan)
        with retailer.account_lock():
            result = retailer.client().add_to_cart(product_code, quantity, fulfillment)
            write_json(PROFILE / "cart-last-write.json", result)
            return {"status": "write_returned", "next": "Verify the quantity using view_cart"}

    app.run(transport="stdio")
