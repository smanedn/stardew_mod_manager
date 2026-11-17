from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from src.core.nexus_browser import (
    browse_nexus_mods,
    fetch_nexus_category,
    fetch_nexus_thumbnail,
    search_nexus_mods,
)


class _FakeResp:
    def __init__(self, payload: Any) -> None:
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._data


def test_fetch_nexus_category_parses_results_and_requires_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="API Key"):
        fetch_nexus_category("trending", "")

    def fake_urlopen(req: urllib.request.Request, timeout: float = 15.0) -> Any:
        assert req.full_url.endswith("/trending.json")
        return _FakeResp(
            [
                {
                    "mod_id": 1915,
                    "name": "Content Patcher",
                    "summary": "Loads content packs.",
                    "author": "Pathoschild",
                    "version": "2.0.0",
                    "endorsement_count": 50000,
                }
            ]
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    mods = fetch_nexus_category("trending", "my-key")
    assert len(mods) == 1
    assert mods[0].mod_id == "1915"
    assert mods[0].name == "Content Patcher"
    assert mods[0].endorsements == 50000


def test_search_nexus_mods_parses_graphql_response(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="search term"):
        search_nexus_mods("   ")

    def fake_urlopen(req: urllib.request.Request, timeout: float = 15.0) -> Any:
        assert "graphql" in req.full_url
        return _FakeResp(
            {
                "data": {
                    "mods": {
                        "nodes": [
                            {
                                "modId": 3753,
                                "name": "Stardew Valley Expanded",
                                "summary": "Huge expansion mod.",
                                "author": "FlashShifter",
                                "version": "1.15.0",
                                "endorsements": 120000,
                            }
                        ]
                    }
                }
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    results = search_nexus_mods("Expanded")
    assert len(results) == 1
    assert results[0].mod_id == "3753"
    assert results[0].author == "FlashShifter"


def test_fetch_nexus_category_handles_401(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_401(req: urllib.request.Request, timeout: float = 15.0) -> Any:
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", raise_401)
    with pytest.raises(ValueError, match="HTTP 401"):
        fetch_nexus_category("latest_updated", "bad-key")


def test_browse_nexus_mods_clamps_pagination_and_parses_picture_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(req: urllib.request.Request, timeout: float = 15.0) -> Any:
        body = json.loads((req.data or b"{}").decode("utf-8"))
        assert body["variables"]["count"] == 100
        assert body["variables"]["offset"] == 50
        return _FakeResp(
            {
                "data": {
                    "mods": {
                        "nodes": [
                            {
                                "modId": 1915,
                                "name": "Content Patcher",
                                "summary": "Loads content packs.",
                                "author": "Pathoschild",
                                "version": "2.0.0",
                                "endorsements": 50000,
                                "pictureUrl": "https://staticdelivery.nexusmods.com/mods/1303/images/1915.png",
                            }
                        ]
                    }
                }
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    mods = browse_nexus_mods(sort_by="endorsements", count=200, offset=50)
    assert len(mods) == 1
    assert mods[0].picture_url.startswith("https://")
    assert fetch_nexus_thumbnail("http://insecure.example.com/a.png") is None
