import json
import os
from pathlib import Path
from urllib.parse import urlencode

import pytest
import requests

from shopping_agent import retailer, private


@pytest.mark.parametrize("url", [
    "https://evil.example/steal", "http://api.pcexpress.ca/pcx-bff/api/v1/products/123_EA",
    "https://api.pcexpress.ca.evil.example/pcx-bff/api/v1/products/123_EA",
    "https://api.pcexpress.ca/pcx-bff/api/v1/checkout",
    "https://api.pcexpress.ca/pcx-bff/api/v1/products/../../checkout",
    "https://user@api.pcexpress.ca/pcx-bff/api/v1/products/123_EA",
])
def test_unexpected_destination_or_route_never_reaches_transport(monkeypatch, url):
    def forbidden(*args, **kwargs):
        pytest.fail("Blocked request reached the HTTP transport")
    monkeypatch.setattr(requests.Session, "request", forbidden)
    with pytest.raises(retailer.RetailerError):
        retailer.RestrictedSession().get(url)


def test_redirects_not_followed_and_deadline_enforced(monkeypatch):
    def response(*args, **kwargs):
        assert kwargs["allow_redirects"] is False
        assert kwargs["timeout"] == (10, 30)
        result = requests.Response()
        result.status_code = 307
        result.headers["Location"] = "https://evil.example/steal"
        return result
    monkeypatch.setattr(requests.Session, "request", response)
    with pytest.raises(retailer.RetailerError, match="redirect blocked"):
        retailer.RestrictedSession().post(retailer.cfg.TOKEN_ENDPOINT, data={"refresh_token": "dummy"})


@pytest.mark.parametrize("response", [
    "bare-code", "com.loblaw.pcx://pcx-android/login/appredirect?code=dummy",
    "com.loblaw.pcx://pcx-android/login/appredirect?code=dummy&state=wrong",
    "https://evil.example/?code=dummy&state=expected",
    "com.loblaw.pcx://pcx-android/login/appredirect?code=dummy&state=expected&state=wrong",
])
def test_login_rejects_unbound_responses(response):
    with pytest.raises(retailer.RetailerError):
        retailer.extract_login_code(response, "expected")


def test_matching_login_response():
    url = retailer.cfg.REDIRECT_URI + "?" + urlencode({"code": "dummy", "state": "expected"})
    assert retailer.extract_login_code(url, "expected") == "dummy"


def test_token_save_is_private_and_corrupt_state_does_not_use_env(tmp_path, monkeypatch):
    monkeypatch.setattr(retailer, "PROFILE", tmp_path)
    private.write_json(tmp_path / "auth" / "pcid_token_state.json", {"refresh_token": "dummy"})
    manager = retailer.PrivateTokens()
    manager._access_token = "dummy-access"
    manager._save()
    path = tmp_path / "auth" / "pcid_token_state.json"
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert not list(path.parent.glob(".write-*"))
    path.write_text("invalid json")
    monkeypatch.setenv("PCEXPRESS_REFRESH_TOKEN", "must-not-reuse")
    with pytest.raises(retailer.RetailerError):
        retailer.PrivateTokens()


def test_provigo_mapping_and_wrong_banner_cart_cannot_be_changed(monkeypatch):
    api = retailer.ProvigoAPI(object(), "1234")
    assert api.domain == "www.provigo.ca"
    assert api.banner == "provigo"
    monkeypatch.setattr(api, "get_cart", lambda: {"bannerId": "zehrs", "customer": {"name": "Test"}})
    with pytest.raises(retailer.RetailerError, match="verified"):
        api.add_to_cart("123_EA", 1)


@pytest.mark.parametrize("quantity", [-1, 1.5, True, 100])
def test_bad_quantities_rejected_before_network(quantity):
    with pytest.raises(retailer.RetailerError):
        retailer.ProvigoAPI(object(), "1234").add_to_cart("123_EA", quantity)


def test_failed_cart_write_is_not_replayed_on_another_cart(monkeypatch):
    api = retailer.ProvigoAPI(object(), "1234")
    api._cart_id = "cart-one"
    calls = []
    def fail(*args, **kwargs):
        calls.append(args)
        raise retailer.RetailerError("HTTP 400")
    monkeypatch.setattr(api, "_request", fail)
    with pytest.raises(retailer.RetailerError):
        api._request_cart("POST", "/carts/{cart_id}", json={})
    assert len(calls) == 1
    assert calls[0][1].endswith("/carts/cart-one")


def test_no_proxy_environment_or_netrc():
    assert retailer.RestrictedSession().trust_env is False


def test_initialization_preserves_existing_preferences(tmp_path, monkeypatch):
    monkeypatch.setattr(private, "PROFILE", tmp_path / ".profile")
    private.initialize()
    path = private.PROFILE / "preferences.json"
    private.write_json(path, {"already_saved": True})
    private.initialize()
    assert private.read_json(path) == {"already_saved": True}
