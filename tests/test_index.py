# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from src.resolver.index import (
    LayeredCacheStore,
    MemoryCacheStore,
    PackageNotFound,
    PyPIIndex,
    releases_from_files,
)
from tests.conftest import make_index
from tests.fakepypi import FakePyPI


def test_releases_from_files_groups_and_filters():
    rows = [
        ["demo-1.0-py3-none-any.whl", "u", None, False, True],
        ["demo-1.0.tar.gz", "u", None, False, False],
        ["demo-2.0-cp312-cp312-manylinux_2_17_x86_64.whl", "u", ">=3.12", False, True],
        ["demo-0.9.egg", "u", None, False, False],  # never installable
        ["other-1.0-py3-none-any.whl", "u", None, False, True],  # wrong project
        ["demo-notaversion.tar.gz", "u", None, False, False],
    ]
    releases = releases_from_files("Demo", rows)
    assert [str(r.version) for r in releases] == ["2.0", "1.0"]
    assert len(releases[1].files) == 2
    assert releases[1].files[1].tags is None  # sdist
    assert releases[0].files[0].requires_python == ">=3.12"


async def test_index_caches_and_deduplicates_requests():
    fake = FakePyPI({"a": {"1.0": {"deps": ["b"]}}})
    index = make_index(fake)
    first, second = await asyncio.gather(index.releases("a"), index.releases("A"))
    assert (
        [str(r.version) for r in first] == ["1.0"] == [str(r.version) for r in second]
    )
    assert fake.count("/simple/a/") == 1
    deps = await index.dependencies("a", first[0])
    await index.dependencies("a", first[0])
    assert deps == ["b"]
    assert fake.count(".metadata") == 1
    await index.client.aclose()


async def test_unknown_project_raises_and_is_cached():
    fake = FakePyPI({})
    index = make_index(fake)
    for _ in range(2):
        with pytest.raises(PackageNotFound):
            await index.releases("nope")
    assert fake.count("/simple/nope/") == 1
    await index.client.aclose()


async def test_metadata_failure_falls_back_to_json_api():
    fake = FakePyPI({"a": {"1.0": {"deps": ["b>=1"]}}})
    original = fake.handle

    def broken_metadata(request):
        if str(request.url).endswith(".metadata"):
            return httpx.Response(500)
        return original(request)

    fake.transport = httpx.MockTransport(broken_metadata)
    index = make_index(fake)
    release = (await index.releases("a"))[0]
    assert await index.dependencies("a", release) == ["b>=1"]
    await index.client.aclose()


async def test_version_info_404_is_empty():
    index = make_index(FakePyPI({"a": {"1.0": {}}}))
    info = await index.version_info("a", "9.9")
    assert info.vulnerabilities == [] and info.requires_dist is None
    await index.client.aclose()


async def test_memory_cache_ttl_and_lru():
    cache = MemoryCacheStore(max_entries=2)
    await cache.set("a", 1)
    await cache.set("b", 2, fetched_at=datetime.now(timezone.utc) - timedelta(hours=2))
    assert await cache.get("a", None) == 1
    assert await cache.get("b", timedelta(hours=1)) is None  # expired
    assert await cache.get("b", None) == 2  # no TTL: still there
    await cache.set("c", 3)  # evicts least recently used ("a" was used before "b")
    assert await cache.get("a", None) is None
    assert await cache.get("c", None) == 3


async def test_layered_cache_promotes_back_hits():
    back = MemoryCacheStore()
    layered = LayeredCacheStore(back)
    await back.set("k", {"v": 1})
    assert await layered.get("k", None) == {"v": 1}
    assert await layered.front.get("k", None) == {"v": 1}
    await layered.set("n", 5)
    assert await back.get("n", None) == 5
    assert await layered.get("missing", None) is None


async def test_simple_api_requested_with_pep691_accept_header():
    seen = {}

    def handler(request):
        seen["accept"] = request.headers.get("accept")
        return httpx.Response(200, json={"files": []})

    index = PyPIIndex(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        MemoryCacheStore(),
        simple_url="https://x/simple",
    )
    with pytest.raises(PackageNotFound):
        await index.releases("a")
    assert seen["accept"] == "application/vnd.pypi.simple.v1+json"
    await index.client.aclose()


async def test_bridge_stops_resolver_thread_when_cancelled():
    import threading

    from src.resolver.index import ResolutionCancelled, SyncIndexBridge

    hang = asyncio.Event()  # never set: a PyPI request that never returns

    class HangingIndex:
        async def releases(self, name):
            await hang.wait()

    bridge = SyncIndexBridge(HangingIndex(), asyncio.get_running_loop())
    outcome = {}

    def resolver_thread():
        try:
            bridge.get_releases("anything")
        except ResolutionCancelled:
            outcome["cancelled"] = True

    thread = threading.Thread(target=resolver_thread)
    thread.start()
    await asyncio.sleep(0.1)
    bridge.cancelled.set()  # what a check timeout does
    await asyncio.to_thread(thread.join, 5)
    assert outcome == {"cancelled": True}
    # Already-cancelled bridges refuse new work immediately.
    with pytest.raises(ResolutionCancelled):
        await asyncio.to_thread(bridge.get_releases, "other")


async def test_parsed_releases_are_reused_until_the_rows_are_refetched(monkeypatch):
    from src.resolver import index as index_module

    parsed = []
    real = index_module.releases_from_files
    monkeypatch.setattr(
        index_module,
        "releases_from_files",
        lambda *args: parsed.append(args[0]) or real(*args),
    )
    index = make_index(FakePyPI({"a": {"1.0": {}, "2.0": {}}}))
    first = await index.releases("a")
    second = await index.releases("A")
    assert parsed == ["a"]  # parsed once for both calls
    assert first[0] is second[0]  # the Release objects are shared...
    first.reverse()
    assert [str(r.version) for r in second] == ["2.0", "1.0"]  # ...the list is not
    # The cache expiring means fresh rows (a new object), which are parsed again.
    index.cache._data.clear()
    await index.releases("a")
    assert parsed == ["a", "a"]


async def test_parsed_releases_cache_is_bounded(monkeypatch):
    from src.resolver import index as index_module

    monkeypatch.setattr(index_module, "PARSED_RELEASES_MAX", 2)
    index = make_index(FakePyPI({name: {"1.0": {}} for name in "abc"}))
    for name in "abc":
        await index.releases(name)
    assert list(index._parsed) == ["b", "c"]  # the oldest project went


async def _drain(bridge):
    """Wait for the bridge's background prefetches (thread-safe futures)."""
    await asyncio.gather(*(asyncio.wrap_future(f) for f in list(bridge._background)))


async def test_layered_cache_serves_repeat_reads_from_memory():
    back = MemoryCacheStore()
    layered = LayeredCacheStore(back)
    await layered.set("k", {"v": 1})
    back._data.clear()  # the shared store is gone; the in-process copy answers
    assert await layered.get("k", None) == {"v": 1}


async def test_prefetch_failure_is_only_a_hint(monkeypatch):
    from src.resolver.index import SyncIndexBridge

    async def index_down(self, name):
        raise RuntimeError("index down")

    index = make_index(FakePyPI({"a": {"1.0": {}}}))
    monkeypatch.setattr(PyPIIndex, "file_rows", index_down)
    bridge = SyncIndexBridge(index, asyncio.get_running_loop())
    bridge.prefetch_releases(["a"])
    await _drain(bridge)  # finishes without raising
    assert not bridge._background


async def test_dependency_prefetch_stops_at_the_limit(monkeypatch):
    from src.resolver.index import SyncIndexBridge

    asked = []

    async def record(self, name, release, preferred_tags=None):
        asked.append(str(release.version))
        return []

    index = make_index(
        FakePyPI({"a": {version: {} for version in ("1.0", "2.0", "3.0", "4.0")}})
    )
    releases = await index.releases("a")  # newest first
    monkeypatch.setattr(PyPIIndex, "dependencies", record)
    bridge = SyncIndexBridge(index, asyncio.get_running_loop(), prefetch_limit=2)
    bridge.prefetch_dependencies("a", releases)
    await _drain(bridge)
    assert asked == ["4.0", "3.0"]


async def test_bridge_waits_for_a_slow_request_that_was_not_cancelled():
    from src.resolver.index import SyncIndexBridge

    async def slow():
        await asyncio.sleep(0.7)  # longer than the bridge's 0.5 s poll
        return "done"

    bridge = SyncIndexBridge(object(), asyncio.get_running_loop())
    assert await asyncio.to_thread(bridge._run, slow()) == "done"
