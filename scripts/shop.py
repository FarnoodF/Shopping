#!/usr/bin/env python3
"""Project entrypoint; invoke using .venv/bin/python -I scripts/shop.py."""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shopping_agent.private import PROFILE, ROOT, initialize, read_json, write_json


def main():
    parser = argparse.ArgumentParser(description="Private meal planning and Provigo shopping")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "status", "login-start", "login-finish", "cart", "customer", "mcp"):
        commands.add_parser(name)
    week = commands.add_parser("new-week")
    week.add_argument("date", help="YYYY-MM-DD")
    week.add_argument("--days", type=int, choices=range(1, 8), help="Coverage length; defaults to the private profile, then seven")
    plan = commands.add_parser("list")
    plan.add_argument("date", help="YYYY-MM-DD")
    search = commands.add_parser("search")
    search.add_argument("query")
    product = commands.add_parser("product")
    product.add_argument("code")
    store = commands.add_parser("store")
    store.add_argument("id")
    change = commands.add_parser("set-quantity")
    change.add_argument("code")
    change.add_argument("quantity", type=int)
    change.add_argument("--fulfillment", choices=("pickup", "delivery"), required=True)
    change.add_argument("--week", required=True, help="The prepared YYYY-MM-DD plan")
    args = parser.parse_args()
    os.umask(0o077)
    initialize()
    if args.command == "init":
        return {"status": "initialized", "profile": str(PROFILE)}
    if args.command == "status":
        prefs = read_json(PROFILE / "preferences.json")
        return {"profile_interview": prefs["interview_status"],
                "login_present": (PROFILE / "auth" / "pcid_token_state.json").exists(),
                "connection": read_json(PROFILE / "connection.json")}
    if args.command in ("new-week", "list"):
        stamp = date.fromisoformat(args.date).isoformat()
        path = PROFILE / "weeks" / stamp / "plan.json"
        if args.command == "new-week":
            if path.exists():
                raise ValueError("This week already exists; update it instead of overwriting it")
            data = read_json(ROOT / "config" / "week.template.json")
            data["start_date"] = stamp
            prefs = read_json(PROFILE / "preferences.json")
            data["days"] = args.days or prefs.get("eating", {}).get("shopping_coverage_days") or 7
            data["people"] = prefs.get("household", {}).get("people")
            data["meal_slots"] = prefs.get("eating", {}).get("shopping_meal_slots") or []
            write_json(path, data)
            return {"plan": str(path)}
        from shopping_agent.planner import compile_list
        result = compile_list(read_json(path))
        write_json(path.parent / "shopping-list.json", result)
        return result
    from shopping_agent import retailer
    if args.command == "mcp":
        from shopping_agent.mcp_server import run
        run()
        return None
    with retailer.account_lock():
        if args.command == "login-start":
            return {"authorize_url": retailer.login_start(), "expires_in_minutes": 15}
        if args.command == "login-finish":
            return retailer.login_finish()
        if args.command == "customer":
            # Discover the store without dumping addresses, loyalty information, or names.
            api = retailer.ProvigoAPI(retailer.PrivateTokens(), "0000")
            raw = api.get_customer()
            write_json(PROFILE / "auth" / "customer.json", raw)
            return {"homeStore": raw.get("homeStore"), "has_cart": bool(raw.get("cartId"))}
        if args.command == "store":
            api = retailer.ProvigoAPI(retailer.PrivateTokens(), args.id)
            result = api._request("GET", api.BASE_URL + "/pickup-locations/" + args.id,
                                  params={"bannerId": "provigo"}).json()
            return {key: result.get(key) for key in ("storeId", "name", "pickupLocationId", "timeZone")}
        api = retailer.client()
        if args.command == "search":
            return api.search_products(args.query)
        if args.command == "product":
            return api.get_product_details(args.code)
        if args.command == "cart":
            result = api.get_cart()
            write_json(PROFILE / "cart-latest.json", result)
            return result
        if args.command == "set-quantity":
            check_week(args.week)
            # Intentional one operation; the skill reconciles actual quantities after every write.
            result = api.add_to_cart(args.code, args.quantity, args.fulfillment)
            write_json(PROFILE / "cart-last-write.json", result)
            return {"status": "write_returned", "verification": "Read cart and compare the resulting quantity"}


def check_week(stamp):
    from shopping_agent.planner import compile_list
    stamp = date.fromisoformat(stamp).isoformat()
    prefs = read_json(PROFILE / "preferences.json")
    plan = read_json(PROFILE / "weeks" / stamp / "plan.json")
    if prefs["food"]["allergies"] is None or prefs["food"]["dietary_restrictions"] is None:
        raise ValueError("Record allergies and dietary restrictions, including explicit none, before shopping")
    if not plan.get("user_choices_recorded"):
        raise ValueError("Record this week's requested meals before shopping")
    compile_list(plan)


if __name__ == "__main__":
    try:
        output = main()
        if output is not None:
            print(json.dumps(output, indent=2, ensure_ascii=False))
    except (ValueError, KeyError, OSError) as error:
        print(f"Cannot continue: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        # Retailer errors are deliberately sanitized; unexpected exceptions must not dump credentials.
        if type(error).__name__ == "RetailerError":
            print(str(error), file=sys.stderr)
        else:
            print("Unexpected response; stop and inspect the local state before retrying.", file=sys.stderr)
        sys.exit(1)
