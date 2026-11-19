from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from src.core.smapi_installer import download_and_extract_smapi, fetch_latest_smapi_release


class _DummyResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _DummyResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_fetch_latest_smapi_release(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "tag_name": "v4.1.10",
        "html_url": "https://github.com/Pathoschild/SMAPI/releases/tag/4.1.10",
        "assets": [
            {
                "name": "SMAPI-4.1.10-installer.zip",
                "browser_download_url": "https://example.com/SMAPI-4.1.10-installer.zip",
            }
        ],
    }
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_a, **_kw: _DummyResponse(json.dumps(payload).encode("utf-8")),
    )
    rel = fetch_latest_smapi_release()
    assert rel is not None
    assert rel.version == "4.1.10"
    assert rel.download_url.endswith("SMAPI-4.1.10-installer.zip")


def test_download_and_extract_smapi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("SMAPI 4.1.10 installer/install on Windows.bat", "@echo off\n")
    zip_bytes = buf.getvalue()

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_a, **_kw: _DummyResponse(zip_bytes),
    )
    installer_dir = download_and_extract_smapi(
        "https://example.com/SMAPI-4.1.10-installer.zip", tmp_path / "smapi"
    )
    assert (installer_dir / "install on Windows.bat").is_file()
