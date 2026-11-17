from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import pytest

from src.core.nexus_installer import NexusTarget, install_from_nexus, parse_nexus_input


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1915", NexusTarget(mod_id="1915")),
        (
            "https://www.nexusmods.com/stardewvalley/mods/1915?tab=files",
            NexusTarget(mod_id="1915"),
        ),
        (
            "nxm://stardewvalley/mods/1915/files/98765?key=abc&expires=999999",
            NexusTarget(mod_id="1915", file_id="98765", nxm_key="abc", nxm_expires="999999"),
        ),
    ],
)
def test_parse_nexus_input_variants(raw: str, expected: NexusTarget) -> None:
    assert parse_nexus_input(raw) == expected


@pytest.mark.parametrize(
    "bad_input",
    ["", "   ", "not-a-url", "nxm://skyrim/mods/1/files/2", "nxm://stardewvalley/mods/1"],
)
def test_parse_nexus_input_rejects_invalid(bad_input: str) -> None:
    with pytest.raises(ValueError):
        parse_nexus_input(bad_input)


def test_install_from_nexus_downloads_and_extracts_mod(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("ContentPatcher/manifest.json", '{"Name": "Content Patcher"}')
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

    def fake_urlopen(req: urllib.request.Request, timeout: float = 15.0) -> Any:
        url = req.full_url
        if url.endswith("/mods/1915/files.json"):
            payload = {
                "files": [
                    {"file_id": 100, "category_name": "OLD_VERSION", "uploaded_timestamp": 10},
                    {"file_id": 200, "category_name": "MAIN", "uploaded_timestamp": 20},
                ]
            }
            return _FakeResp(json.dumps(payload).encode("utf-8"))
        if "/mods/1915/files/200/download_link.json" in url:
            payload = [{"URI": "https://cdn.example.com/ContentPatcher.zip"}]
            return _FakeResp(json.dumps(payload).encode("utf-8"))
        if url == "https://cdn.example.com/ContentPatcher.zip":
            return _FakeResp(zip_bytes)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    modpack = tmp_path / "modpacks" / "Default"
    installed = install_from_nexus(
        "https://www.nexusmods.com/stardewvalley/mods/1915",
        api_key="test-key",
        modpack_dir=modpack,
    )
    assert installed == ["ContentPatcher"]
    assert (modpack / "ContentPatcher" / "manifest.json").is_file()


def test_install_from_nexus_handles_403_free_account_and_missing_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ValueError, match="API key is required"):
        install_from_nexus("1915", api_key="", modpack_dir=tmp_path)

    def raise_403(req: urllib.request.Request, timeout: float = 15.0) -> Any:
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", raise_403)
    with pytest.raises(ValueError, match="nxm://"):
        install_from_nexus("1915", api_key="test-key", modpack_dir=tmp_path)
