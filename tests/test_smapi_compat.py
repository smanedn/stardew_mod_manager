from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from src.core.mod_scanner import ModInfo
from src.core.smapi_compat import check_smapi_compatibility


def test_check_smapi_compatibility_parses_statuses_and_caches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mods = [
        ModInfo(
            folder_name="GoodMod",
            name="Good Mod",
            version="2.0.0",
            path=tmp_path / "GoodMod",
            unique_id="Author.GoodMod",
        ),
        ModInfo(
            folder_name="OldMod",
            name="Old Mod",
            version="1.0.0",
            path=tmp_path / "OldMod",
            unique_id="Author.OldMod",
        ),
        ModInfo(
            folder_name="BrokenMod",
            name="Broken Mod",
            version="0.9.0",
            path=tmp_path / "BrokenMod",
            unique_id="Author.BrokenMod",
        ),
    ]

    calls = 0

    class _FakeResp:
        def __enter__(self) -> _FakeResp:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                [
                    {
                        "id": "Author.GoodMod",
                        "metadata": {"compatibilityStatus": "Ok", "compatibilitySummary": ""},
                    },
                    {
                        "id": "Author.OldMod",
                        "metadata": {
                            "compatibilityStatus": "Unofficial",
                            "compatibilitySummary": "Use unofficial 1.6 build.",
                            "unofficialUpdate": {
                                "version": "1.1.0-unofficial",
                                "url": "https://smapi.io/mods",
                            },
                        },
                    },
                    {
                        "id": "Author.BrokenMod",
                        "metadata": {
                            "compatibilityStatus": "Broken",
                            "compatibilitySummary": "No longer works in 1.6.",
                        },
                    },
                ]
            ).encode("utf-8")

    def fake_urlopen(req: urllib.request.Request, timeout: float = 10.0) -> Any:
        nonlocal calls
        calls += 1
        return _FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    cache_file = tmp_path / "compat_cache.json"

    res = check_smapi_compatibility(mods, cache_path=cache_file)
    assert calls == 1
    assert res["GoodMod"].status == "Ok"
    assert not res["GoodMod"].is_broken and not res["GoodMod"].is_warning
    assert res["OldMod"].is_warning
    assert res["OldMod"].unofficial_version == "1.1.0-unofficial"
    assert res["BrokenMod"].is_broken

    # Second call hits cache
    res_cached = check_smapi_compatibility(mods, cache_path=cache_file)
    assert calls == 1
    assert res_cached["BrokenMod"].is_broken


def test_check_smapi_compatibility_handles_offline_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mods = [
        ModInfo(
            folder_name="ModA",
            name="Mod A",
            version="1.0.0",
            path=tmp_path / "ModA",
            unique_id="Author.ModA",
        )
    ]

    def raise_offline(req: urllib.request.Request, timeout: float = 10.0) -> Any:
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", raise_offline)
    assert check_smapi_compatibility(mods, cache_path=tmp_path / "c.json") == {}
