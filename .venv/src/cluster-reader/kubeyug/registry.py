from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from platformdirs import user_cache_dir 

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(HERE), "data")
PACKAGED_TOOL_REGISTRY_PATH = os.path.join(DATA_DIR, "tool_registry.json")

DEFAULT_TTL_SECONDS = int(os.getenv("KUBEYUG_REGISTRY_TTL_SECONDS", str(24 * 3600)))
REGISTRY_URL = os.getenv("KUBEYUG_REGISTRY_URL") 

_APP_NAME = "kubeyug"
_CACHE_DIR = Path(user_cache_dir(_APP_NAME))
_CACHE_REGISTRY_PATH = _CACHE_DIR / "tool_registry.json"
_CACHE_META_PATH = _CACHE_DIR / "tool_registry.meta.json"

_TOOL_REGISTRY_CACHE: dict[str, Any] | None = None


@dataclass
class _CacheMeta:
    fetched_at: float | None = None
    etag: str | None = None

    @staticmethod
    def load(path: Path) -> "_CacheMeta":
        if not path.exists():
            return _CacheMeta()
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            return _CacheMeta(
                fetched_at=float(obj.get("fetchedAt")) if obj.get("fetchedAt") is not None else None,
                etag=str(obj.get("etag")) if obj.get("etag") else None,
            )
        except Exception:
            return _CacheMeta()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"fetchedAt": self.fetched_at, "etag": self.etag}, indent=2),
            encoding="utf-8",
        )


def _read_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _should_refresh(meta: _CacheMeta) -> bool:
    if meta.fetched_at is None:
        return True
    return (time.time() - meta.fetched_at) > DEFAULT_TTL_SECONDS


def _http_fetch_registry(url: str, meta: _CacheMeta) -> tuple[dict[str, Any] | None, str | None]:
    """
    Returns: (registry_json_or_none_if_304, new_etag_or_none)
    """
    headers = {
        "Accept": "application/json",
        "User-Agent": "kubeyug/0.1",
    }
    if meta.etag:
        headers["If-None-Match"] = meta.etag 

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = getattr(resp, "status", 200)
            if status == 304:
                return None, meta.etag
            body = resp.read().decode("utf-8")
            new_etag = resp.headers.get("ETag")
            return json.loads(body), new_etag
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return None, meta.etag
        raise


def _refresh_cache_if_needed() -> None:
    """
    Try to ensure we have a fresh-ish cached registry on disk.
    This never prevents kubeyug from running: failures should fall back to cache/packaged.
    """
    if not REGISTRY_URL:
        return

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    meta = _CacheMeta.load(_CACHE_META_PATH)

    if _CACHE_REGISTRY_PATH.exists() and not _should_refresh(meta):
        return

    try:
        reg, new_etag = _http_fetch_registry(REGISTRY_URL, meta)
        if reg is not None:
            _CACHE_REGISTRY_PATH.write_text(json.dumps(reg, indent=2), encoding="utf-8")
            meta.etag = new_etag or meta.etag
        meta.fetched_at = time.time()
        meta.save(_CACHE_META_PATH)
    except Exception:
        return


def load_tool_registry() -> dict[str, Any]:
    global _TOOL_REGISTRY_CACHE
    if _TOOL_REGISTRY_CACHE is not None:
        return _TOOL_REGISTRY_CACHE

    _refresh_cache_if_needed()

    if _CACHE_REGISTRY_PATH.exists():
        _TOOL_REGISTRY_CACHE = _read_json_file(_CACHE_REGISTRY_PATH)
        return _TOOL_REGISTRY_CACHE

    _TOOL_REGISTRY_CACHE = json.loads(Path(PACKAGED_TOOL_REGISTRY_PATH).read_text(encoding="utf-8"))
    return _TOOL_REGISTRY_CACHE


def find_tool(key: str) -> tuple[str, dict] | None:
    reg = load_tool_registry()
    for category, tools in reg.items():
        for t in tools:
            if t.get("key") == key:
                return category, t
    return None


def list_registry_tools() -> list[dict]:
    reg = load_tool_registry()
    out: list[dict] = []
    for category, tools in reg.items():
        for t in tools:
            out.append({"category": category, **t})
    return out
