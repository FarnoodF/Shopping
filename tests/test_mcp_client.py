import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "shopping_mcp_call", Path(__file__).resolve().parents[1] / "scripts/mcp_call.py"
)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


@pytest.mark.parametrize("destination", ["/tmp/account.json", "../account.json", "week/../../account.json"])
def test_mcp_results_cannot_be_written_outside_private_profile(destination, tmp_path, monkeypatch):
    monkeypatch.setattr(client, "PROFILE", tmp_path / "profile")
    with pytest.raises(ValueError):
        client.private_output(destination)


def test_mcp_results_reject_symlinked_parent(tmp_path, monkeypatch):
    profile = tmp_path / "profile"
    profile.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (profile / "linked").symlink_to(elsewhere, target_is_directory=True)
    monkeypatch.setattr(client, "PROFILE", profile)
    with pytest.raises(ValueError, match="symlinks"):
        client.private_output("linked/cart.json")


def test_mcp_results_reject_symlinked_file(tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text("sensitive")
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / "cart.json").symlink_to(elsewhere)
    monkeypatch.setattr(client, "PROFILE", profile)
    with pytest.raises(ValueError, match="symlinks"):
        client.private_output("cart.json")
