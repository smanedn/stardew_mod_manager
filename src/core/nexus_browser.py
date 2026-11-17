"""Browse and search Stardew Valley mods on Nexus Mods."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal

_NEXUS_API_V1 = "https://api.nexusmods.com/v1/games/stardewvalley/mods"
_NEXUS_GRAPHQL = "https://api.nexusmods.com/v2/graphql"

BrowseCategory = Literal["trending", "latest_updated", "latest_added"]
BrowseSort = Literal["endorsements", "updatedAt", "createdAt"]


@dataclass(frozen=True)
class NexusModSummary:
    """Lightweight metadata for a Nexus Mods entry shown in the browser."""

    mod_id: str
    name: str
    summary: str
    author: str
    version: str
    endorsements: int = 0
    picture_url: str = ""


def _parse_v1_mod_list(payload: Any) -> list[NexusModSummary]:
    if not isinstance(payload, list):
        return []
    mods: list[NexusModSummary] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        mod_id = item.get("mod_id")
        name = str(item.get("name") or "").strip()
        if not mod_id or not name:
            continue
        mods.append(
            NexusModSummary(
                mod_id=str(mod_id),
                name=name,
                summary=str(item.get("summary") or "").strip(),
                author=str(item.get("author") or "Unknown").strip(),
                version=str(item.get("version") or "?").strip(),
                endorsements=int(item.get("endorsement_count") or 0),
                picture_url=str(item.get("picture_url") or "").strip(),
            )
        )
    return mods


def fetch_nexus_category(
    category: BrowseCategory, api_key: str, timeout: float = 15.0
) -> list[NexusModSummary]:
    """Fetch trending, latest_updated, or latest_added Stardew Valley mods."""
    clean_key = api_key.strip()
    if not clean_key:
        raise ValueError("Enter your Nexus Mods API Key above to browse mods.")

    url = f"{_NEXUS_API_V1}/{category}.json"
    req = urllib.request.Request(
        url,
        headers={
            "apikey": clean_key,
            "Accept": "application/json",
            "User-Agent": "SVMM-NexusBrowser",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise ValueError("Invalid Nexus Mods API key (HTTP 401).") from exc
        raise ValueError(f"Nexus Mods API error (HTTP {exc.code}).") from exc

    return _parse_v1_mod_list(payload)


def _parse_graphql_nodes(payload: Any) -> list[NexusModSummary]:
    if not isinstance(payload, dict):
        return []
    nodes = payload.get("data", {}).get("mods", {}).get("nodes", [])
    if not isinstance(nodes, list):
        return []

    results: list[NexusModSummary] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        mod_id = node.get("modId")
        name = str(node.get("name") or "").strip()
        if not mod_id or not name:
            continue
        results.append(
            NexusModSummary(
                mod_id=str(mod_id),
                name=name,
                summary=str(node.get("summary") or "").strip(),
                author=str(node.get("author") or "Unknown").strip(),
                version=str(node.get("version") or "?").strip(),
                endorsements=int(node.get("endorsements") or 0),
                picture_url=str(node.get("pictureUrl") or "").strip(),
            )
        )
    return results


def _post_graphql(gql: str, variables: dict[str, Any], timeout: float = 15.0) -> Any:
    body = json.dumps({"query": gql, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        _NEXUS_GRAPHQL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SVMM-NexusBrowser",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Nexus browse failed (HTTP {exc.code}).") from exc


def browse_nexus_mods(
    sort_by: BrowseSort = "endorsements",
    count: int = 25,
    offset: int = 0,
    timeout: float = 15.0,
) -> list[NexusModSummary]:
    """Browse Stardew Valley mods via Nexus Mods v2 GraphQL API with pagination (10-100)."""
    clamped_count = max(10, min(100, count))
    gql = f"""
    query BrowseStardewMods($count: Int!, $offset: Int!) {{
      mods(
        filter: {{
          gameDomainName: {{ value: "stardewvalley", op: EQUALS }}
        }}
        sort: [{{ {sort_by}: {{ direction: DESC }} }}]
        count: $count
        offset: $offset
      ) {{
        nodes {{
          modId
          name
          summary
          author
          version
          endorsements
          pictureUrl
        }}
      }}
    }}
    """
    payload = _post_graphql(
        gql, {"count": clamped_count, "offset": max(0, offset)}, timeout=timeout
    )
    return _parse_graphql_nodes(payload)


def search_nexus_mods(
    query: str, count: int = 25, offset: int = 0, timeout: float = 15.0
) -> list[NexusModSummary]:
    """Search Stardew Valley mods by name via Nexus Mods v2 GraphQL API."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Enter a search term.")

    clamped_count = max(10, min(100, count))
    gql = """
    query SearchStardewMods($name: String!, $count: Int!, $offset: Int!) {
      mods(
        filter: {
          gameDomainName: { value: "stardewvalley", op: EQUALS }
          name: { value: $name, op: WILDCARD }
        }
        sort: [{ endorsements: { direction: DESC } }]
        count: $count
        offset: $offset
      ) {
        nodes {
          modId
          name
          summary
          author
          version
          endorsements
          pictureUrl
        }
      }
    }
    """
    payload = _post_graphql(
        gql,
        {"name": clean_query, "count": clamped_count, "offset": max(0, offset)},
        timeout=timeout,
    )
    return _parse_graphql_nodes(payload)


def fetch_nexus_thumbnail(url: str, timeout: float = 8.0) -> bytes | None:
    """Download mod thumbnail image bytes from an https:// URL, or return None on failure."""
    clean = url.strip()
    if not clean.startswith("https://"):
        return None
    req = urllib.request.Request(clean, headers={"User-Agent": "SVMM-NexusBrowser"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return bytes(resp.read())
    except (OSError, urllib.error.URLError):
        return None
