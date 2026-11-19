from __future__ import annotations

import json

import pytest

from src.core.app_updater import check_svmm_update


class _DummyResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._data = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _DummyResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_check_svmm_update_detects_newer_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_a, **_kw: _DummyResponse(
            {
                "tag_name": "v1.0.0",
                "html_url": "https://github.com/smanedn/stardew_mod_manager/releases/tag/v1.0.0",
            }
        ),
    )
    res = check_svmm_update("0.8.0")
    assert res == (
        "1.0.0",
        "https://github.com/smanedn/stardew_mod_manager/releases/tag/v1.0.0",
    )
    assert check_svmm_update("1.0.0") is None
    assert check_svmm_update("1.2.0") is None
