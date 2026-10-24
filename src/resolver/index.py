# -*- coding: utf-8 -*-
"""
Package index access for the resolver.

`PyPIIndex` is async: it shares one httpx connection pool across every check
running in the process, caches responses in a `CacheStore`, and de-duplicates
concurrent requests for the same key.

resolvelib, however, is synchronous and calls back into the provider for one
package at a time. `SyncIndexBridge` lets the resolver run in a worker thread
while all I/O stays on the app's event loop - the thread blocks on each call
while the loop is free to run prefetches and other checks.

Data sources, in order of preference (the same ones pip uses):
- release files: the Simple API's JSON form (PEP 691), which carries each
  file's Requires-Python, yanked flag and whether core metadata exists;
- dependencies: the `.metadata` file next to a wheel (PEP 658/714), i.e. the
  wheel's METADATA without downloading the wheel;
- fallback / vulnerabilities: the JSON API's per-version endpoint.
"""

import asyncio
import threading
from collections import OrderedDict
from collections.abc import Awaitable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol, TypeVar

import httpx
from loguru import logger
from packaging.metadata import parse_email
from packaging.tags import Tag
from packaging.utils import (
    InvalidSdistFilename,
    InvalidWheelFilename,
    canonicalize_name,
    parse_sdist_filename,
    parse_wheel_filename,
)
from packaging.version import InvalidVersion, Version

T = TypeVar("T")

SIMPLE_JSON = "application/vnd.pypi.simple.v1+json"
# Projects whose parsed releases are kept in memory (see PyPIIndex.releases).
PARSED_RELEASES_MAX = 1024


class PackageNotFound(LookupError):
    """The index has no project by this name."""


class ResolutionCancelled(Exception):
    """Raised inside the resolver thread when the check timed out."""


@dataclass(frozen=True)
class DistFile:
    filename: str
    url: str
    requires_python: str | None
    yanked: bool
    has_metadata: bool
    # None for an sdist; the wheel's compatibility tags otherwise.
    tags: frozenset[Tag] | None

    @property
    def is_wheel(self) -> bool:
        return self.tags is not None


@dataclass
class Release:
    version: Version
    files: list[DistFile] = field(default_factory=list)

    @property
    def yanked(self) -> bool:
        return bool(self.files) and all(f.yanked for f in self.files)


@dataclass(frozen=True)
class VersionInfo:
    requires_dist: list[str] | None
    vulnerabilities: list[dict]
    summary: str | None = None


class SyncIndex(Protocol):
    """What the resolvelib provider needs. Tests implement it with fixtures."""

    def get_releases(self, name: str) -> list[Release]: ...

    def get_dependencies(self, name: str, release: Release) -> list[str] | None: ...

    def prefetch_releases(self, names: Iterable[str]) -> None: ...

    def prefetch_dependencies(self, name: str, releases: Iterable[Release]) -> None: ...


def releases_from_files(project: str, files: list[list]) -> list[Release]:
    """Group cached Simple API file rows by version, newest first."""
    by_version: dict[Version, Release] = {}
    canonical = canonicalize_name(project)
    for filename, url, requires_python, yanked, has_metadata in files:
        try:
            if filename.endswith(".whl"):
                name, version, _build, tags = parse_wheel_filename(filename)
            elif filename.endswith((".tar.gz", ".zip")):
                name, version = parse_sdist_filename(filename)
                tags = None
            else:
                continue  # .egg, .exe, .msi, .rpm: never installable by pip
        except InvalidWheelFilename, InvalidSdistFilename, InvalidVersion:
            continue
        if name != canonical:
            continue
        release = by_version.setdefault(version, Release(version))
        release.files.append(
            DistFile(
                filename, url, requires_python, bool(yanked), bool(has_metadata), tags
            )
        )
    return [by_version[v] for v in sorted(by_version, reverse=True)]


# --------------------------------------------------------------------------
# caching
# --------------------------------------------------------------------------


class CacheStore(Protocol):
    async def get(self, key: str, max_age: timedelta | None) -> Any | None: ...

    async def set(self, key: str, payload: Any) -> None: ...


class MemoryCacheStore:
    """Process-local LRU cache; used alone by tests and in front of the
    database cache in the app (see LayeredCacheStore)."""

    def __init__(self, max_entries: int = 50_000) -> None:
        self.max_entries = max_entries
        self._data: OrderedDict[str, tuple[datetime, Any]] = OrderedDict()

    async def get(self, key: str, max_age: timedelta | None) -> Any | None:
        hit = self._data.get(key)
        if hit is None:
            return None
        fetched_at, payload = hit
        if max_age is not None and datetime.now(timezone.utc) - fetched_at > max_age:
            return None
        self._data.move_to_end(key)
        return payload

    async def set(
        self, key: str, payload: Any, fetched_at: datetime | None = None
    ) -> None:
        self._data[key] = (fetched_at or datetime.now(timezone.utc), payload)
        self._data.move_to_end(key)
        while len(self._data) > self.max_entries:
            self._data.popitem(last=False)


class LayeredCacheStore:
    """Memory in front of a shared store. Backtracking over a package like
    botocore asks for the metadata of hundreds of releases, so a per-lookup
    database round trip dominates a warm resolution; this keeps those hits
    in-process while the shared store still lets other workers reuse them."""

    def __init__(self, back: CacheStore, front: MemoryCacheStore | None = None) -> None:
        self.front = front or MemoryCacheStore()
        self.back = back

    async def get(self, key: str, max_age: timedelta | None) -> Any | None:
        payload = await self.front.get(key, max_age)
        if payload is not None:
            return payload
        payload = await self.back.get(key, max_age)
        if payload is not None:
            # The back store's own fetch time is unknown here, so a promoted
            # entry may live up to one extra TTL in this process.
            await self.front.set(key, payload)
        return payload

    async def set(self, key: str, payload: Any) -> None:
        await self.front.set(key, payload)
        await self.back.set(key, payload)


# --------------------------------------------------------------------------
# async PyPI client
# --------------------------------------------------------------------------


class PyPIIndex:
    def __init__(
        self,
        client: httpx.AsyncClient,
        cache: CacheStore,
        *,
        simple_url: str = "https://pypi.org/simple",
        json_url: str = "https://pypi.org/pypi",
        index_ttl: timedelta = timedelta(hours=1),
        version_info_ttl: timedelta = timedelta(days=1),
    ) -> None:
        self.client = client
        self.cache = cache
        self.simple_url = simple_url.rstrip("/")
        self.json_url = json_url.rstrip("/")
        self.index_ttl = index_ttl
        self.version_info_ttl = version_info_ttl
        # One in-flight request per key, shared by every caller in the process.
        self._inflight: dict[str, asyncio.Task] = {}
        # Parsed releases per project, with the cached rows they came from.
        # Parsing ~100k wheel filenames was a third of a warm check's CPU, and
        # the rows only change when the cache refetches them (a new object).
        self._parsed: OrderedDict[str, tuple[list[list], list[Release]]] = OrderedDict()

    async def _once(self, key: str, max_age: timedelta | None, fetch) -> Any:
        cached = await self.cache.get(key, max_age)
        if cached is not None:
            return cached
        task = self._inflight.get(key)
        if task is None:
            task = asyncio.ensure_future(self._fetch_and_store(key, fetch))
            self._inflight[key] = task
            task.add_done_callback(lambda _t: self._inflight.pop(key, None))
        # Shielded: the fetch is shared by every check waiting on this key,
        # so one caller being cancelled (a timed-out check) must not cancel
        # it for the others.
        return await asyncio.shield(task)

    async def _fetch_and_store(self, key: str, fetch) -> Any:
        payload = await fetch()
        await self.cache.set(key, payload)
        return payload

    async def file_rows(self, name: str) -> list[list]:
        canonical = canonicalize_name(name)

        async def fetch() -> list[list]:
            response = await self.client.get(
                f"{self.simple_url}/{canonical}/", headers={"Accept": SIMPLE_JSON}
            )
            if response.status_code == 404:
                return []  # cached too: an unknown name stays unknown for the TTL
            response.raise_for_status()
            return [
                [
                    f["filename"],
                    f["url"],
                    f.get("requires-python"),
                    bool(f.get("yanked")),
                    bool(f.get("core-metadata") or f.get("data-dist-info-metadata")),
                ]
                for f in response.json().get("files", [])
            ]

        return await self._once(f"simple:{canonical}", self.index_ttl, fetch)

    async def releases(self, name: str) -> list[Release]:
        rows = await self.file_rows(name)
        if not rows:
            raise PackageNotFound(name)
        canonical = canonicalize_name(name)
        hit = self._parsed.get(canonical)
        if hit is not None and hit[0] is rows:
            self._parsed.move_to_end(canonical)
            releases = hit[1]
        else:
            releases = releases_from_files(name, rows)
            self._parsed[canonical] = (rows, releases)
            while len(self._parsed) > PARSED_RELEASES_MAX:
                self._parsed.popitem(last=False)
        # A copy of the list: callers share the Release objects (never
        # mutated after parsing) but must not reorder another check's list.
        return list(releases)

    async def version_info(self, name: str, version: str) -> VersionInfo:
        canonical = canonicalize_name(name)

        async def fetch() -> dict:
            response = await self.client.get(
                f"{self.json_url}/{canonical}/{version}/json"
            )
            if response.status_code == 404:
                return {"requires_dist": None, "vulnerabilities": [], "summary": None}
            response.raise_for_status()
            data = response.json()
            return {
                "requires_dist": data["info"].get("requires_dist"),
                "summary": data["info"].get("summary"),
                "vulnerabilities": [
                    {
                        "id": v.get("id"),
                        "aliases": v.get("aliases", []),
                        "summary": v.get("summary") or (v.get("details") or "")[:300],
                        "fixed_in": v.get("fixed_in", []),
                        "link": v.get("link"),
                    }
                    for v in data.get("vulnerabilities", [])
                    if not v.get("withdrawn")
                ],
            }

        payload = await self._once(
            f"version:{canonical}:{version}", self.version_info_ttl, fetch
        )
        return VersionInfo(**payload)

    async def dependencies(
        self, name: str, release: Release, preferred_tags: frozenset[Tag] | None = None
    ) -> list[str] | None:
        """Requires-Dist for a release, or None when no source has it."""
        canonical = canonicalize_name(name)
        version = str(release.version)
        with_metadata = [f for f in release.files if f.has_metadata]
        # Wheels for different platforms can (rarely) declare different
        # dependencies, so read the one the target would actually install.
        with_metadata.sort(
            key=lambda f: not (preferred_tags and f.tags and f.tags & preferred_tags)
        )
        if with_metadata:
            chosen = with_metadata[0]

            async def fetch() -> list[str]:
                response = await self.client.get(f"{chosen.url}.metadata")
                response.raise_for_status()
                raw, _unparsed = parse_email(response.content)
                return list(raw.get("requires_dist", []))

            try:
                # Published files never change, so no expiry.
                return await self._once(
                    f"deps:{canonical}:{version}:{chosen.filename}", None, fetch
                )
            except httpx.HTTPError as exc:
                logger.warning(
                    f"metadata fetch failed for {chosen.filename}: {exc}; falling back to JSON API"
                )

        info = await self.version_info(name, version)
        if info.requires_dist is not None:
            return list(info.requires_dist)
        # The JSON API reports null both for "no dependencies" and "unknown".
        # When the release has wheels its metadata was extracted, so null
        # means none; for an sdist-only release we genuinely don't know.
        return [] if any(f.is_wheel for f in release.files) else None


# --------------------------------------------------------------------------
# bridge for the resolver thread
# --------------------------------------------------------------------------


class SyncIndexBridge:
    """Adapts PyPIIndex for a resolver running in a worker thread."""

    def __init__(
        self,
        index: PyPIIndex,
        loop: asyncio.AbstractEventLoop,
        preferred_tags: frozenset[Tag] | None = None,
        prefetch_limit: int = 3,
    ) -> None:
        self.index = index
        self.loop = loop
        self.preferred_tags = preferred_tags
        self.prefetch_limit = prefetch_limit
        self.cancelled = threading.Event()
        self._releases: dict[str, list[Release] | PackageNotFound] = {}
        self._deps: dict[tuple[str, Version], list[str] | None] = {}
        self._background: set[asyncio.Future] = set()

    def _run(self, coro: Awaitable[T]) -> T:
        if self.cancelled.is_set():
            coro.close()  # created by the caller; never scheduled
            raise ResolutionCancelled()
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        # Poll instead of a single blocking wait so the resolver thread
        # notices `cancelled` (the check timed out) even if a request hangs.
        while True:
            try:
                return future.result(timeout=0.5)
            except TimeoutError:
                if self.cancelled.is_set():
                    future.cancel()
                    raise ResolutionCancelled() from None

    def _spawn(self, coro) -> None:
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        self._background.add(future)
        future.add_done_callback(self._background.discard)

    def get_releases(self, name: str) -> list[Release]:
        canonical = canonicalize_name(name)
        if canonical not in self._releases:
            try:
                self._releases[canonical] = self._run(self.index.releases(canonical))
            except PackageNotFound as exc:
                self._releases[canonical] = exc
        found = self._releases[canonical]
        if isinstance(found, PackageNotFound):
            raise found
        return found

    def get_dependencies(self, name: str, release: Release) -> list[str] | None:
        key = (canonicalize_name(name), release.version)
        if key not in self._deps:
            self._deps[key] = self._run(
                self.index.dependencies(name, release, self.preferred_tags)
            )
        return self._deps[key]

    async def _quiet(self, coro) -> None:
        try:
            await coro
        except (
            Exception
        ) as exc:  # a prefetch is only a hint; the real call reports errors
            logger.debug(f"prefetch failed: {exc}")

    def prefetch_releases(self, names: Iterable[str]) -> None:
        for name in names:
            if canonicalize_name(name) not in self._releases:
                self._spawn(self._quiet(self.index.file_rows(name)))

    def prefetch_dependencies(self, name: str, releases: Iterable[Release]) -> None:
        for count, release in enumerate(releases):
            if count >= self.prefetch_limit:
                break
            if (canonicalize_name(name), release.version) not in self._deps:
                self._spawn(
                    self._quiet(
                        self.index.dependencies(name, release, self.preferred_tags)
                    )
                )

    def cached_releases(self, name: str) -> list[Release] | None:
        found = self._releases.get(canonicalize_name(name))
        return None if found is None or isinstance(found, PackageNotFound) else found
