from __future__ import annotations

from pathlib import Path

import pytest

from src.core.smapi_log import parse_smapi_log


def test_parse_smapi_log_extracts_errors_and_warnings(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        parse_smapi_log(missing)

    log_file = tmp_path / "SMAPI-latest.txt"
    log_file.write_text(
        "\ufeff[12:00:01 INFO  SMAPI] SMAPI 4.1.10 with Stardew Valley 1.6.15\n"
        "[12:00:02 WARN  SMAPI] Found 1 mod with warnings.\n"
        "[12:00:03 ERROR SMAPI] Failed loading mod BrokenMod\n"
        "[12:00:04 ALERT SMAPI] Critical issue detected\n",
        encoding="utf-8",
    )

    summary = parse_smapi_log(log_file)
    assert len(summary.errors) == 2
    assert len(summary.warnings) == 1
    assert "BrokenMod" in summary.errors[0]
    assert "Critical issue" in summary.errors[1]
    assert "1 mod with warnings" in summary.warnings[0]
