from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import pytest

from src.core.mod_scanner import ModInfo
from src.core.updater import (
    GitHubUpdateProvider,
    NexusUpdateProvider,
    UpdateChecker,
    UpdateResult,
    can_direct_update,
    install_mod_update,
    is_newer_version,
)


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


def test_nexus_provider_requires_api_key_and_parses_mod_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    no_key = NexusUpdateProvider(api_key="")
    assert not no_key.supports("Nexus:1915")

    with_key = NexusUpdateProvider(api_key="my-nexus-key")
    assert with_key.supports("Nexus:1915")
    assert with_key.supports("Nexus:1915@ContentPatcher")
    assert not with_key.supports("GitHub:owner/repo")

    captured_headers: dict[str, str] = {}

    class _FakeResp:
        def __enter__(self) -> _FakeResp:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"version": "2.3.1"}).encode("utf-8")

    def fake_urlopen(req: urllib.request.Request, timeout: float = 5.0) -> Any:
        captured_headers.update({k.lower(): v for k, v in req.header_items()})
        return _FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    latest = with_key.fetch_latest("Nexus:1915@optional")
    assert latest == ("2.3.1", "https://www.nexusmods.com/stardewvalley/mods/1915")
    assert captured_headers.get("apikey") == "my-nexus-key"


def test_install_mod_update_downloads_github_zip_asset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("MyMod/manifest.json", '{"Name": "MyMod", "Version": "2.0.0"}')
    zip_bytes = zip_buf.getvalue()

    class _FakeResp:
        def __init__(self, data: bytes) -> None:
            self._stream = io.BytesIO(data)

        def __enter__(self) -> _FakeResp:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            return self._stream.read(size)

    monkeypatch.setattr(urllib.request, "urlopen", lambda _req, timeout=30.0: _FakeResp(zip_bytes))

    modpack = tmp_path / "modpacks" / "Default"
    res = UpdateResult(
        folder_name="MyMod",
        mod_name="MyMod",
        current_version="1.0.0",
        latest_version="2.0.0",
        url="https://github.com/user/repo/releases/tag/v2.0.0",
        download_url="https://github.com/user/repo/releases/download/v2.0.0/MyMod.zip",
        update_key="GitHub:user/repo",
        has_update=True,
    )
    installed = install_mod_update(res, modpack)
    assert installed == ["MyMod"]
    assert '"2.0.0"' in (modpack / "MyMod" / "manifest.json").read_text(encoding="utf-8")


def test_can_direct_update_checks_provider_and_key() -> None:
    gh_ok = UpdateResult(
        folder_name="A",
        mod_name="A",
        current_version="1.0",
        latest_version="2.0",
        download_url="https://github.com/u/r/releases/download/v2.0/A.zip",
        update_key="GitHub:u/r",
        has_update=True,
    )
    gh_no_zip = UpdateResult(
        folder_name="B",
        mod_name="B",
        current_version="1.0",
        latest_version="2.0",
        update_key="GitHub:u/r",
        has_update=True,
    )
    nexus = UpdateResult(
        folder_name="C",
        mod_name="C",
        current_version="1.0",
        latest_version="2.0",
        update_key="Nexus:1915",
        has_update=True,
    )
    assert can_direct_update(gh_ok)
    assert not can_direct_update(gh_no_zip)
    assert not can_direct_update(nexus, has_nexus_key=False)
    assert can_direct_update(nexus, has_nexus_key=True)
