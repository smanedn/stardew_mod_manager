from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from src.core.mod_scanner import ModInfo
from src.core.updater import GitHubUpdateProvider, UpdateChecker, is_newer_version


class _FakeProvider:
    def __init__(self, responses: dict[str, tuple[str, str] | Exception]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def supports(self, update_key: str) -> bool:
        return update_key.startswith("GitHub:")

    def fetch_latest(self, update_key: str, timeout: float = 5.0) -> tuple[str, str] | None:
        self.calls.append(update_key)
        val = self.responses[update_key]
        if isinstance(val, Exception):
            raise val
        return val


def test_version_comparison() -> None:
    assert is_newer_version("1.0.0", "1.0.1")
    assert is_newer_version("1.2", "1.2.1")
    assert not is_newer_version("2.0.0", "1.9.9")
    assert not is_newer_version("1.0.0", "1.0.0")


def test_update_checker_caches_results_and_handles_offline(tmp_path: Path) -> None:
    cache_file = tmp_path / "update_cache.json"
    mods = [
        ModInfo(
            folder_name="ModA",
            name="Mod A",
            version="1.0.0",
            path=tmp_path / "ModA",
            update_keys=("GitHub:owner/mod-a",),
        ),
        ModInfo(
            folder_name="ModB",
            name="Mod B",
            version="2.0.0",
            path=tmp_path / "ModB",
            update_keys=("GitHub:owner/mod-b",),
        ),
    ]
    provider = _FakeProvider(
        {
            "GitHub:owner/mod-a": ("1.2.0", "https://github.com/owner/mod-a/releases/tag/v1.2.0"),
            "GitHub:owner/mod-b": urllib.error.URLError("offline"),
        }
    )

    checker = UpdateChecker(providers=[provider], cache_path=cache_file, cache_ttl_seconds=3600)
    results = checker.check_mods(mods)
    assert len(results) == 2
    assert results[0].has_update and results[0].latest_version == "1.2.0"
    assert results[1].error is not None

    # Second run should use cache for ModA without calling provider again
    provider.calls.clear()
    results_cached = checker.check_mods([mods[0]])
    assert results_cached[0].has_update
    assert provider.calls == []


def test_github_provider_fetches_release_with_optional_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_headers: dict[str, str] = {}

    class _FakeResp:
        def __enter__(self) -> _FakeResp:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "tag_name": "v2.5.0",
                    "html_url": "https://github.com/user/repo/releases/tag/v2.5.0",
                }
            ).encode("utf-8")

    def fake_urlopen(req: urllib.request.Request, timeout: float = 5.0) -> Any:
        captured_headers.update(dict(req.header_items()))
        return _FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    provider = GitHubUpdateProvider(token="user-secret-token")
    assert provider.supports("GitHub:user/repo")
    assert not provider.supports("Nexus:1234")
    latest = provider.fetch_latest("GitHub:user/repo")
    assert latest == ("2.5.0", "https://github.com/user/repo/releases/tag/v2.5.0")
    assert captured_headers.get("Authorization") == "Bearer user-secret-token"
    assert isinstance(io.BytesIO(), io.BytesIO)
