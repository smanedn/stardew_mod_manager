"""Parse SMAPI-latest.txt into structured errors, warnings, and full log text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_ERROR_LINE_RE = re.compile(r"^\[\d{2}:\d{2}:\d{2}\s+(?:ERROR|ALERT)\b", re.IGNORECASE)
_WARN_LINE_RE = re.compile(r"^\[\d{2}:\d{2}:\d{2}\s+WARN\b", re.IGNORECASE)


@dataclass(frozen=True)
class SmapiLogSummary:
    """Parsed summary of a SMAPI-latest.txt log file."""

    path: Path
    errors: list[str]
    warnings: list[str]
    raw_text: str


def parse_smapi_log(log_path: str | Path) -> SmapiLogSummary:
    """Read SMAPI-latest.txt and extract ERROR/ALERT and WARN entries."""
    path = Path(log_path)
    if not path.is_file():
        raise FileNotFoundError(f"SMAPI log not found: {path}")

    raw_text = path.read_text(encoding="utf-8-sig", errors="replace")
    errors: list[str] = []
    warnings: list[str] = []

    for line in raw_text.splitlines():
        if _ERROR_LINE_RE.match(line):
            errors.append(line)
        elif _WARN_LINE_RE.match(line):
            warnings.append(line)

    return SmapiLogSummary(
        path=path,
        errors=errors,
        warnings=warnings,
        raw_text=raw_text,
    )
