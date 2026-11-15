"""Use the pinned upstream API client with local storage and restricted transport.

No upstream setup/login script, HTTP server, container, or browser automation runs.
"""
import base64
import contextlib
import fcntl
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sys
import time
from urllib.parse import parse_qs, urlencode, urlsplit

from .private import PROFILE, ROOT, initialize, private_dir, read_json, write_json


def verify_source():
    source = ROOT / "vendor" / "pcexpress-mcp-server"
    reviewed = read_json(ROOT / "config" / "upstream-review.json")
    for name, digest in reviewed["files"].items():
        path = source / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Upstream source differs from the reviewed version; re-audit first")
    # Exclude local import shadowing and unreviewed dotenv/secret overrides.
    if set(p.name for p in source.glob("*.py")) != set(reviewed["files"]):
        raise ValueError("Unexpected Python modules in upstream checkout")
    if any(p.is_dir() and p.name != "__pycache__" and (p / "__init__.py").exists()
           for p in source.iterdir()):
        raise ValueError("Unexpected importable package in upstream checkout")
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    # Use the reviewed app constant, not an arbitrary file in the home directory.
    # Extract it as a literal before importing the upstream config module.
    import ast
    tree = ast.parse((source / "pcid_config.py").read_text())
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_BAKED_CLIENT_SECRET" for t in statement.targets
        ):
            os.environ["PCEXPRESS_CLIENT_SECRET"] = ast.literal_eval(statement.value)
    os.environ.pop("PCEXPRESS_CLIENT_ID", None)
    sys.path.insert(0, str(source))


verify_source()
import requests
import pcid_config as cfg
from pcid_token import PcidAuthError, TokenManager
from pcexpress_mcp_server import PCExpressAPI

logging.getLogger("pcexpress-mcp").setLevel(logging.CRITICAL)
IDENTIFIER = r"[A-Za-z0-9_-]+"
API_PREFIX = "/pcx-bff/api/v1"


class RetailerError(Exception):
    """Safe-to-display error containing no credentials or response body."""


class RestrictedSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.trust_env = False  # no inherited proxies or .netrc credentials

    def request(self, method, url, **kwargs):
        parsed = urlsplit(url)
        method = method.upper()
        valid = (parsed.scheme == "https" and parsed.port in (None, 443)
                 and not parsed.username and not parsed.password and not parsed.fragment)
        allowed = False
        if parsed.hostname == "accounts.pcid.ca":
            allowed = method == "POST" and parsed.path == "/oauth2/v1/token" and not parsed.query
        elif parsed.hostname == "api.pcexpress.ca":
            routes = {
                "GET": [r"/ecommerce/v2/provigo/customers", rf"/customers/{IDENTIFIER}/carts",
                        rf"/carts/{IDENTIFIER}", rf"/products/{IDENTIFIER}",
                        r"/pickup-locations/[0-9]{4}"],
                "POST": [r"/products/search", rf"/carts/{IDENTIFIER}"],
            }
            allowed = any(re.fullmatch(API_PREFIX + route, parsed.path)
                          for route in routes.get(method, []))
            if parsed.query not in ("", "inventory=true"):
                allowed = False
        if not valid or not allowed:
            raise RetailerError("Request outside the allowed retailer routes was blocked")
        if kwargs.get("verify") is False:
            raise RetailerError("TLS verification cannot be disabled")
        kwargs.update(timeout=(10, 30), allow_redirects=False)
        try:
            response = super().request(method, url, **kwargs)
        except requests.RequestException:
            raise RetailerError("Retailer request failed; inspect the basket before retrying a change") from None
        if 300 <= response.status_code < 400:
            raise RetailerError("Retailer redirect blocked; credentials were not forwarded")
        return response


class PrivateTokens(TokenManager):
    def __init__(self):
        self._state_path = str(PROFILE / "auth" / "pcid_token_state.json")
        import threading
        self._lock = threading.Lock()
        self._session = RestrictedSession()
        try:
            state = read_json(PROFILE / "auth" / "pcid_token_state.json")
            self._refresh_token = state["refresh_token"]
            self._access_token = state.get("access_token")
            self._expires_at = float(state.get("expires_at", 0))
            if not isinstance(self._refresh_token, str) or not self._refresh_token:
                raise ValueError()
        except (OSError, ValueError, KeyError, TypeError):
            raise RetailerError("A valid local PC ID login is needed") from None

    def _save(self):
        write_json(PROFILE / "auth" / "pcid_token_state.json", {
            "refresh_token": self._refresh_token,
            "access_token": self._access_token,
            "expires_at": self._expires_at,
        })

    def _refresh_now(self):
        try:
            return super()._refresh_now()
        except (PcidAuthError, KeyError, ValueError):
            raise RetailerError("PC ID refresh failed; sign in again if the saved token was revoked") from None


class ProvigoAPI(PCExpressAPI):
    BANNER_DOMAINS = {"provigo": "www.provigo.ca"}

    def __init__(self, tokens, store_id):
        if not re.fullmatch(r"[0-9]{4}", str(store_id)):
            raise RetailerError("A verified four-digit Provigo store ID is required")
        super().__init__(tokens, None, str(store_id), "provigo")
        self.session = RestrictedSession()

    def _request(self, method, url, **kwargs):
        try:
            return super()._request(method, url, **kwargs)
        except requests.HTTPError as error:
            raise RetailerError(f"Retailer returned HTTP {error.response.status_code}; no change was retried") from None

    def _request_cart(self, method, path, **kwargs):
        # Re-read rather than silently replaying a mutation against a different cart.
        return self._request(method, self.BASE_URL + path.format(cart_id=self.cart_id), **kwargs)

    def search_products(self, query, size=12):
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            raise RetailerError("Use a search phrase between 1 and 200 characters")
        if type(size) is not int or not 1 <= size <= 48:
            raise RetailerError("Search size must be 1–48")
        # Upstream requires a cart for search; the API reference says it is optional.
        data = self._request("POST", self.BASE_URL + "/products/search", json={
            "lang": "en", "term": query, "storeId": self.store_id, "banner": "provigo",
            "pagination": {"from": 0, "size": size},
        }).json()
        keys = ("code", "articleNumber", "name", "brand", "packageSize", "prices",
                "dealPrice", "stockStatus", "link", "offerType")
        return {"products": [{key: item.get(key) for key in keys}
                             for item in data.get("results", [])[:size]],
                "totalResults": data.get("pagination", {}).get("totalResults")}

    def get_product_details(self, product_code):
        validate_product(product_code)
        return super().get_product_details(product_code)

    def add_to_cart(self, product_code, quantity=1, fulfillment_method="pickup"):
        validate_product(product_code)
        if type(quantity) is not int or not 0 <= quantity <= 99:
            raise RetailerError("Quantity must be a whole number between 0 and 99")
        if fulfillment_method not in ("pickup", "delivery"):
            raise RetailerError("Choose pickup or delivery")
        cart = self.get_cart()
        if not self._cart_matches_banner(cart) or not cart.get("customer"):
            raise RetailerError("Cart could not be verified as an open, signed-in Provigo cart")
        return super().add_to_cart(product_code, quantity, fulfillment_method)


def validate_product(code):
    if not isinstance(code, str) or not re.fullmatch(r"[0-9]+_[A-Z0-9]+", code):
        raise RetailerError("Use a product code returned by Provigo search")


@contextlib.contextmanager
def account_lock():
    initialize()
    path = PROFILE / "auth" / "account.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RetailerError("Another shopping process is using this login") from None
        yield


def client():
    connection = read_json(PROFILE / "connection.json")
    return ProvigoAPI(PrivateTokens(), connection["store_id"])


def login_start():
    def b64(raw):
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")
    verifier = b64(secrets.token_bytes(64))
    state = b64(secrets.token_bytes(24))
    challenge = b64(hashlib.sha256(verifier.encode()).digest())
    params = {"client_id": cfg.CLIENT_ID, "response_type": "code", "scope": cfg.SCOPE,
              "redirect_uri": cfg.REDIRECT_URI, "code_challenge": challenge,
              "code_challenge_method": "S256", "state": state, "nonce": b64(secrets.token_bytes(16))}
    write_json(PROFILE / "auth" / "pending.json", {
        "verifier": verifier, "state": state, "created_at": time.time(),
    })
    return cfg.AUTHORIZE_ENDPOINT + "?" + urlencode(params)


def extract_login_code(url, expected_state):
    parsed = urlsplit(url.strip())
    expected = urlsplit(cfg.REDIRECT_URI)
    if (parsed.scheme, parsed.netloc, parsed.path) != (expected.scheme, expected.netloc, expected.path):
        raise RetailerError("Expected the complete PC Express app redirect URL")
    values = parse_qs(parsed.query)
    states, codes = values.get("state", []), values.get("code", [])
    if ("error" in values or len(states) != 1 or len(codes) != 1 or not expected_state
            or not hmac.compare_digest(states[0], expected_state)):
        raise RetailerError("Login response state is missing or mismatched; start a fresh login")
    return codes[0]


def login_finish():
    pending_path = PROFILE / "auth" / "pending.json"
    redirect_path = PROFILE / "auth" / "redirect.txt"
    pending = read_json(pending_path)
    if not 0 <= time.time() - pending["created_at"] <= 900:
        raise RetailerError("Login attempt expired; start a fresh login")
    code = extract_login_code(redirect_path.read_text(), pending["state"])
    response = RestrictedSession().post(cfg.TOKEN_ENDPOINT, data={
        "grant_type": "authorization_code", "code": code, "client_id": cfg.CLIENT_ID,
        "client_secret": cfg.CLIENT_SECRET, "code_verifier": pending["verifier"],
    }, headers={"Accept": "application/json", "User-Agent": "okhttp/4.12.0", **cfg.PCID_HEADERS})
    if response.status_code != 200:
        raise RetailerError(f"PC ID exchange returned HTTP {response.status_code}; start a fresh login")
    data = response.json()
    if not data.get("refresh_token") or not data.get("access_token"):
        raise RetailerError("PC ID did not return the expected credentials")
    write_json(PROFILE / "auth" / "pcid_token_state.json", {
        "refresh_token": data["refresh_token"], "access_token": data["access_token"],
        "expires_at": time.time() + int(data.get("expires_in", 3600)),
    })
    pending_path.unlink()
    redirect_path.unlink()
    return {"status": "signed_in", "credentials": "saved locally; never printed"}
