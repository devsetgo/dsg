# -*- coding: utf-8 -*-
"""Routes, through Robyn's in-process TestClient against the in-memory DB.

TestClient doesn't run startup/shutdown handlers and runs every handler on
its own event loop, so the fixture runs startup on that same loop and
replaces the PyPI index with the fake one.
"""

import asyncio
import json
from pathlib import Path
from urllib.parse import urlencode

import httpx
import pytest
from robyn.testing import TestClient as RobynTestClient

from src import checks, limits, resources
from src.settings import settings
from src.db_init import async_db
from src.main import app
from src.resolver.index import MemoryCacheStore, PyPIIndex
from tests.fakepypi import JSON, SIMPLE, FakePyPI

SPEC = {
    "requests": {
        "2.31.0": {"deps": ["idna"]},
        "2.34.0": {"deps": ["idna"], "requires_python": ">=3.10"},
    },
    "idna": {"3.6": {}, "3.10": {}},
    "conflict-a": {"1.0": {"deps": ["idna<3"]}},
}


@pytest.fixture
def client(monkeypatch):
    # Every test client submits from 127.0.0.1; start each test with a clean slate.
    limits.reset()
    monkeypatch.setattr(settings, "public_history", True)
    test_client = RobynTestClient(app)
    loop = test_client._loop
    loop.run_until_complete(resources.startup())  # memory DB: creates the schema
    loop.run_until_complete(resources.pypi_client.aclose())
    fake = FakePyPI(SPEC)
    resources.pypi_index = PyPIIndex(
        fake.client(), MemoryCacheStore(), simple_url=SIMPLE, json_url=JSON
    )
    yield test_client
    loop.run_until_complete(checks.wait_for_checks())
    loop.run_until_complete(resources.pypi_index.client.aclose())
    # Fresh schema per test.
    loop.run_until_complete(_drop_all())
    test_client.close()


async def _drop_all():
    async with async_db.db_config.engine.begin() as connection:
        await connection.run_sync(async_db.Base.metadata.drop_all)


def post_form(client, data, htmx=True):
    headers = {"content-type": "application/x-www-form-urlencoded"}
    if htmx:
        headers["hx-request"] = "true"
    return client.post("/check", body=urlencode(data), headers=headers)


def submit_and_finish(client, data):
    response = post_form(client, data)
    location = response.headers.get("hx-redirect")
    assert location, response.text[:500]
    client._loop.run_until_complete(checks.wait_for_checks())
    return location


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/check",
        "/about",
        "/history",
        "/stats",
        "/api/health/status",
        "/api/health/uptime",
    ],
)
def test_pages_render(client, path):
    response = client.get(path)
    assert response.status_code == 200, response.text[:500]


def test_health_endpoints_come_from_dsg_lib_without_tracing(client):
    import tracemalloc

    assert client.get("/api/health/status").json() == {"status": "UP"}
    uptime = client.get("/api/health/uptime").json()["uptime"]
    assert set(uptime) == {"Days", "Hours", "Minutes", "Seconds"}
    # Not exposed on a public site, and nothing should be paying for traces.
    assert client.get("/api/health/heapdump").status_code == 404
    assert not tracemalloc.is_tracing()


def test_form_page_uses_mdb_layout_and_schemaform(client):
    html = client.get("/check").text
    assert "mdb-ui-kit@9.3.0" in html
    assert 'id="sidebarMenu"' in html
    assert "pydantic-form" in html and 'name="requirements"' in html


def test_invalid_htmx_post_returns_form_fragment(client):
    response = post_form(client, {"requirements": "", "python_version": "2.7"})
    assert response.status_code == 200
    assert "<html" not in response.text  # fragment for hx-swap, not a page
    assert "invalid-feedback" in response.text


def test_invalid_plain_post_returns_full_page_422(client):
    response = post_form(client, {"requirements": ""}, htmx=False)
    assert response.status_code == 422
    assert "<html" in response.text


def test_check_flow_end_to_end(client):
    location = submit_and_finish(
        client,
        {
            "requirements": "requests==2.31.0",
            "python_version": "3.12",
            "mode": "upgrade",
        },
    )
    status = client.get(f"{location}/status")
    assert status.headers.get("hx-refresh") == "true"
    page = client.get(location).text
    assert "requests==2.34.0" in page
    assert "idna" in page  # transitive table
    history = client.get("/history").text
    assert location in history
    stats = client.get("/stats").text
    assert "requests" in stats


def test_stats_never_list_packages_unknown_to_pypi(client):
    submit_and_finish(
        client,
        {"requirements": "requests\nacme-internal-tools", "mode": "upgrade"},
    )
    stats = client.get("/stats").text
    assert "requests" in stats
    assert "acme-internal-tools" not in stats


def test_python_version_changes_result(client):
    location = submit_and_finish(
        client,
        {"requirements": "requests", "python_version": "3.10", "mode": "upgrade"},
    )
    assert "requests==2.34.0" in client.get(location).text
    # 2.34.0 requires >=3.10, so the same file on 3.10 still gets it; validate an old pin instead
    location = submit_and_finish(
        client,
        {
            "requirements": "requests==2.31.0",
            "python_version": "3.12",
            "mode": "validate",
        },
    )
    assert "requests==2.31.0" in client.get(location).text


def test_conflict_is_rendered(client):
    location = submit_and_finish(
        client,
        {
            "requirements": "conflict-a\nidna>=3",
            "python_version": "3.12",
            "mode": "validate",
        },
    )
    page = client.get(location).text
    assert "can&#39;t be installed" in page or "can't be installed" in page
    assert "conflict-a 1.0 requires idna&lt;3" in page


def test_pending_check_shows_polling_fragment(client):
    request_group_id = client._loop.run_until_complete(
        checks.create_check(
            requirements="requests",
            python_version="3.12",
            platform="linux-x86_64",
            mode="upgrade",
            host_ip=None,
            user_agent=None,
        )
    )
    page = client.get(f"/check/{request_group_id}").text
    assert 'hx-trigger="every 2s"' in page
    fragment = client.get(f"/check/{request_group_id}/status").text
    assert "<html" not in fragment and "Queued" in fragment


def test_unknown_check_is_404(client):
    response = client.get("/check/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    status = client.get("/check/00000000-0000-0000-0000-000000000000/status")
    assert status.headers.get("hx-redirect") == "/check"


def test_plain_post_redirects(client):
    response = post_form(client, {"requirements": "idna"}, htmx=False)
    assert response.status_code == 303
    assert response.headers.get("location").startswith("/check/")


def test_api_check(client):
    response = client.post(
        "/api/check",
        body=json.dumps({"requirements": "requests==2.31.0", "python_version": "3.12"}),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] and payload["url"].startswith("/check/")
    assert {p["name"] for p in payload["packages"]} == {"requests", "idna"}


def test_api_check_validation(client):
    bad = client.post(
        "/api/check",
        body=json.dumps({"python_version": "3.12"}),
        headers={"content-type": "application/json"},
    )
    assert bad.status_code == 422
    assert bad.json()["errors"]
    not_json = client.post(
        "/api/check", body="nope", headers={"content-type": "application/json"}
    )
    assert not_json.status_code == 400


def test_history_pagination_param(client):
    assert client.get("/history", query_params={"page": "x"}).status_code == 200
    assert client.get("/history", query_params={"page": "3"}).status_code == 200


def test_db_cache_store_roundtrip_ttl_and_upsert(client):
    from datetime import timedelta

    from src.pypi_cache import DbCacheStore

    store, run = DbCacheStore(), client._loop.run_until_complete
    assert run(store.get("simple:x", None)) is None
    run(store.set("simple:x", [["x-1.0.tar.gz", "u", None, False, False]]))
    assert run(store.get("simple:x", timedelta(hours=1))) == [
        ["x-1.0.tar.gz", "u", None, False, False]
    ]
    assert run(store.get("simple:x", timedelta(seconds=-1))) is None  # expired
    run(store.set("simple:x", ["replaced"]))
    assert run(store.get("simple:x", None)) == ["replaced"]


def test_stale_checks_are_failed(client):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import update

    from src.db_tables import Check

    run = client._loop.run_until_complete
    request_group_id = run(
        checks.create_check(
            requirements="idna",
            python_version="3.12",
            platform="linux-x86_64",
            mode="upgrade",
            host_ip=None,
            user_agent=None,
        )
    )
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    run(
        resources.db_ops.execute_one(
            update(Check)
            .where(Check.request_group_id == request_group_id)
            .values(date_created=old, date_updated=old)
        )
    )
    # A page view shows it as failed even before the sweep runs...
    assert "did not finish" in client.get(f"/check/{request_group_id}").text
    # ...and the startup sweep persists that.
    run(checks.fail_stale_checks())
    assert run(checks.get_check(request_group_id)).status == "failed"


def test_running_check_without_heartbeat_is_failed(client):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import update

    from src.db_tables import Check

    run = client._loop.run_until_complete
    request_group_id = run(
        checks.create_check(
            requirements="idna",
            python_version="3.12",
            platform="linux-x86_64",
            mode="upgrade",
            host_ip=None,
            user_agent=None,
        )
    )
    beat = datetime.now(timezone.utc) - timedelta(seconds=checks.HEARTBEAT_SECONDS)
    run(
        resources.db_ops.execute_one(
            update(Check)
            .where(Check.request_group_id == request_group_id)
            .values(status="running", date_updated=beat)
        )
    )
    # One missed beat is not enough...
    assert "hx-trigger" in client.get(f"/check/{request_group_id}").text
    dead = datetime.now(timezone.utc) - timedelta(seconds=checks.STALE_SECONDS + 5)
    run(
        resources.db_ops.execute_one(
            update(Check)
            .where(Check.request_group_id == request_group_id)
            .values(date_updated=dead)
        )
    )
    # ...but a silent one is reported failed and swept.
    assert "did not finish" in client.get(f"/check/{request_group_id}").text
    run(checks.fail_stale_checks())
    assert run(checks.get_check(request_group_id)).status == "failed"


# --- privacy, abuse limits, redirects --------------------------------------


def _create(client, requirements="idna"):
    return client._loop.run_until_complete(
        checks.create_check(
            requirements=requirements,
            python_version="3.12",
            platform="linux-x86_64",
            mode="upgrade",
            host_ip=None,
            user_agent=None,
        )
    )


def test_history_is_private_by_default(client, monkeypatch):
    monkeypatch.setattr(settings, "public_history", False)
    location = submit_and_finish(
        client, {"requirements": "idna", "python_version": "3.12"}
    )
    history = client.get("/history").text
    assert (
        "aren&#39;t listed publicly" in history or "aren't listed publicly" in history
    )
    assert location not in history
    assert 'href="/history"' not in client.get("/check").text  # no sidebar link
    assert client.get(location).status_code == 200  # the link itself still works


def test_credentials_in_urls_are_never_stored_or_shown(client):
    text = "--extra-index-url https://deploy:s3cr3t-token@pkgs.example.com/simple\nidna"
    location = submit_and_finish(
        client, {"requirements": text, "python_version": "3.12"}
    )
    check = client._loop.run_until_complete(checks.get_check(location.split("/")[-1]))
    assert "s3cr3t-token" not in check.text_in
    assert "https://****@pkgs.example.com/simple" in check.text_in
    page = client.get(location).text
    assert "s3cr3t-token" not in page
    assert "s3cr3t-token" not in (check.resolved_requirements or "")


def test_rate_limit_per_client(client, monkeypatch):
    monkeypatch.setattr(settings, "checks_per_minute_per_ip", 2)
    data = {"requirements": "idna", "python_version": "3.12"}
    for _ in range(2):
        assert post_form(client, data).headers.get("hx-redirect")
    refused = post_form(client, data)
    assert refused.headers.get("hx-redirect") is None
    assert "Too many checks" in refused.text and 'name="requirements"' in refused.text
    assert post_form(client, data, htmx=False).status_code == 429
    api = client.post(
        "/api/check",
        body=json.dumps({"requirements": "idna"}),
        headers={"content-type": "application/json"},
    )
    assert api.status_code == 429 and "Too many checks" in api.json()["error"]


@pytest.mark.parametrize(
    "hops, forwarded, expected",
    [
        # Traefik appends the real peer; the spoofed leftmost entry is ignored.
        (1, "6.6.6.6, 203.0.113.7", "203.0.113.7"),
        (2, "6.6.6.6, 203.0.113.7, 10.0.0.2", "203.0.113.7"),
        # Fewer entries than proxies: the header can't be trusted at all.
        (2, "203.0.113.7", "10.0.0.1"),
        (0, "6.6.6.6", "10.0.0.1"),
        (1, None, "10.0.0.1"),
    ],
)
def test_client_ip_trusts_only_proxy_appended_entries(
    monkeypatch, hops, forwarded, expected
):
    from types import SimpleNamespace

    from src.routes.pages import client_ip

    monkeypatch.setattr(settings, "forwarded_proxy_hops", hops)
    headers = {"x-forwarded-for": forwarded} if forwarded else {}
    request = SimpleNamespace(headers=headers, ip_addr="10.0.0.1")
    assert client_ip(request) == expected


def test_busy_server_refuses_new_checks(client, monkeypatch):
    monkeypatch.setattr(checks, "queue_is_full", lambda: True)
    refused = post_form(client, {"requirements": "idna"}, htmx=False)
    assert refused.status_code == 429
    assert "busy" in refused.text


def test_queue_places_are_claimed_at_once_and_released(client, monkeypatch):
    monkeypatch.setattr(settings, "max_concurrent_checks", 1)
    monkeypatch.setattr(settings, "max_queued_checks", 1)
    assert checks._in_flight == 0
    # A burst: both places go before any check has started running.
    assert checks.try_reserve() and checks.try_reserve()
    assert not checks.try_reserve()
    checks.release_reservation()
    checks.release_reservation()
    # A full submit-and-run cycle gives its place back.
    submit_and_finish(client, {"requirements": "idna", "python_version": "3.12"})
    assert checks._in_flight == 0


def test_api_store_failure_is_json_and_frees_the_place(client, monkeypatch):
    async def db_down(**kwargs):
        raise RuntimeError("database error: locked: INSERT INTO checks ...")

    monkeypatch.setattr(checks, "create_check", db_down)
    response = client.post(
        "/api/check",
        body=json.dumps({"requirements": "idna"}),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 500
    assert response.json()["error"].startswith("An internal error")
    assert "INSERT" not in response.text
    assert checks._in_flight == 0


@pytest.mark.parametrize(
    "old, new",
    [
        ("/pypi/check", "/check"),
        ("/pypi/index", "/"),
        ("/pages/index", "/"),
        ("/pypi/list", "/stats"),
    ],
)
def test_old_urls_redirect(client, old, new):
    response = client.get(old)
    assert response.status_code == 301
    assert response.headers.get("location") == new


# --- failure paths ----------------------------------------------------------


def test_pypi_outage_fails_the_check_with_a_clear_message(client):
    def offline(request):
        raise httpx.ConnectError("no route to host")

    resources.pypi_index = PyPIIndex(
        httpx.AsyncClient(transport=httpx.MockTransport(offline)),
        MemoryCacheStore(),
        simple_url=SIMPLE,
        json_url=JSON,
    )
    location = submit_and_finish(
        client, {"requirements": "idna", "python_version": "3.12"}
    )
    check = client._loop.run_until_complete(checks.get_check(location.split("/")[-1]))
    assert check.status == "failed"
    assert check.error == "Could not reach PyPI (ConnectError). Try again shortly."


def test_internal_errors_are_not_shown_to_users(client, monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("database error: SELECT secret FROM checks")

    monkeypatch.setattr(checks, "resolve_requirements", broken)
    location = submit_and_finish(
        client, {"requirements": "idna", "python_version": "3.12"}
    )
    check = client._loop.run_until_complete(checks.get_check(location.split("/")[-1]))
    assert check.status == "failed"
    assert "SELECT" not in check.error
    assert check.error == "An internal error stopped this check. It has been logged."


def test_failed_report_save_marks_check_failed(client, monkeypatch):
    async def cannot_store(*args, **kwargs):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(checks, "store_report", cannot_store)
    location = submit_and_finish(
        client, {"requirements": "idna", "python_version": "3.12"}
    )
    check = client._loop.run_until_complete(checks.get_check(location.split("/")[-1]))
    assert check.status == "failed"  # not left "running"


def test_cancelled_check_is_marked_restarted(client, monkeypatch):
    async def forever(*args, **kwargs):
        await asyncio.sleep(3600)

    monkeypatch.setattr(checks, "resolve_requirements", forever)
    request_group_id = _create(client)
    loop = client._loop

    async def start_then_cancel():
        task = checks.schedule_check(request_group_id)
        await asyncio.sleep(0.05)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    loop.run_until_complete(start_then_cancel())
    check = loop.run_until_complete(checks.get_check(request_group_id))
    assert check.status == "failed"
    assert "restarted" in check.error


def test_api_reports_failures_as_json(client, monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(checks, "resolve_requirements", broken)
    response = client.post(
        "/api/check",
        body=json.dumps({"requirements": "idna"}),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 502
    payload = response.json()
    assert payload["error"].startswith("An internal error")
    stored = client._loop.run_until_complete(
        checks.get_check(payload["request_group_id"])
    )
    assert stored.status == "failed"  # not left "pending"


def test_unhandled_exception_page():
    # @app.exception registers the handler but returns None, so read it back.
    response = app.exception_handler(ValueError("boom"))
    assert response.status_code == 500
    assert "boom" not in response.description


def test_startup_refuses_unmigrated_file_database(client, monkeypatch):
    from src.settings import Settings

    monkeypatch.setattr(Settings, "is_memory_db", property(lambda self: False))
    with pytest.raises(RuntimeError, match="not migrated"):
        client._loop.run_until_complete(resources.startup())


# --- background and fallback paths ------------------------------------------


def test_heartbeat_refreshes_the_check_and_survives_a_failed_beat(
    client, monkeypatch, logged
):
    run = client._loop.run_until_complete
    request_group_id = _create(client)
    before = run(checks.get_check(request_group_id)).date_updated
    monkeypatch.setattr(checks, "HEARTBEAT_SECONDS", 0.01)
    real_set, beats = checks._set, []

    async def first_beat_fails(rgid, **values):
        beats.append(rgid)
        if len(beats) == 1:
            raise RuntimeError("database error: locked")
        await real_set(rgid, **values)

    monkeypatch.setattr(checks, "_set", first_beat_fails)

    async def beat_a_few():
        task = asyncio.create_task(checks._heartbeat(request_group_id))
        while len(beats) < 3:
            await asyncio.sleep(0.01)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    run(asyncio.wait_for(beat_a_few(), 5))
    assert run(checks.get_check(request_group_id)).date_updated > before
    assert any("heartbeat" in m for m in logged)


def _db_error():
    from dsg_lib.async_database_functions.database_operations import (
        DatabaseErrorResult,
    )

    return DatabaseErrorResult({"error": "OperationalError", "details": "locked"})


def test_db_cache_store_read_and_write_failures_are_logged_misses(
    client, monkeypatch, logged
):
    from src.pypi_cache import DbCacheStore

    run = client._loop.run_until_complete

    async def read_fails(*args, **kwargs):
        return _db_error()

    async def write_fails(*args, **kwargs):
        return _db_error()

    monkeypatch.setattr(resources.db_ops, "read_one_record", read_fails)
    monkeypatch.setattr(resources.db_ops, "execute_one", write_fails)
    store = DbCacheStore()
    assert run(store.get("simple:x", None)) is None
    run(store.set("simple:x", []))  # must not raise
    assert any("cache read failed" in m for m in logged)
    assert any("cache write failed" in m for m in logged)


def test_history_logs_a_broken_database_instead_of_hiding_it(
    client, monkeypatch, logged
):
    async def broken(*args, **kwargs):
        return _db_error()

    monkeypatch.setattr(resources.db_ops, "count_query", broken)
    monkeypatch.setattr(resources.db_ops, "read_query", broken)
    assert client.get("/history").status_code == 200
    assert any("recent checks unavailable" in m for m in logged)


def test_rate_limit_can_be_disabled(monkeypatch):
    limits.reset()
    monkeypatch.setattr(settings, "checks_per_minute_per_ip", 0)
    assert all(limits.allow("203.0.113.7") for _ in range(50))


def test_rate_limit_table_is_bounded(monkeypatch):
    limits.reset()
    monkeypatch.setattr(settings, "checks_per_minute_per_ip", 1)
    monkeypatch.setattr(limits, "MAX_TRACKED_CLIENTS", 3)
    assert limits.allow("a") and not limits.allow("a")
    for client_address in ("b", "c", "d"):
        limits.allow(client_address)
    assert len(limits._hits) == 3
    # "a" was evicted as the oldest, so it starts a fresh window.
    assert limits.allow("a")
    limits.reset()


def test_form_store_failure_frees_the_queue_place(client, monkeypatch):
    async def db_down(**kwargs):
        raise RuntimeError("database error: locked")

    monkeypatch.setattr(checks, "create_check", db_down)
    # The test client re-raises instead of calling @app.exception (the 500
    # page itself is covered by test_unhandled_exception_page).
    with pytest.raises(RuntimeError):
        post_form(client, {"requirements": "idna"}, htmx=False)
    assert checks._in_flight == 0


# --- gaps found by dsg-coverage-check ----------------------------------------


def test_form_fields_reads_the_str_body_the_live_server_sends():
    from types import SimpleNamespace

    from src.routes.pages import form_fields

    # Robyn 0.88 hands a urlencoded body to handlers as str (checked against a
    # live server); the test client sends bytes, so cover both.
    as_str = SimpleNamespace(form_data={}, body="requirements=idna%0Asix&mode=upgrade")
    assert form_fields(as_str) == {"requirements": "idna\nsix", "mode": "upgrade"}
    as_bytes = SimpleNamespace(form_data={}, body=b"requirements=idna&mode=")
    assert form_fields(as_bytes) == {"requirements": "idna", "mode": ""}
    binary = SimpleNamespace(form_data={}, body=b"requirements=\xff\xfe")
    assert form_fields(binary) == {"requirements": "��"}


def test_form_fields_prefers_parsed_multipart_fields():
    from types import SimpleNamespace

    from src.routes.pages import form_fields

    request = SimpleNamespace(form_data={"requirements": "idna"}, body="ignored")
    assert form_fields(request) == {"requirements": "idna"}


def test_api_rejects_a_json_body_that_is_not_an_object(client):
    response = client.post(
        "/api/check", body="[1, 2]", headers={"content-type": "application/json"}
    )
    assert response.status_code == 400


def test_api_check_with_nothing_to_resolve_stores_a_failed_check_without_packages(
    client,
):
    from sqlalchemy import Select

    from src.db_tables import CheckPackage

    response = client.post(
        "/api/check",
        body=json.dumps({"requirements": "-r base.txt"}),
        headers={"content-type": "application/json"},
    )
    payload = response.json()
    assert response.status_code == 409
    assert payload["error"] == "No requirements to resolve."
    run = client._loop.run_until_complete
    stored = run(checks.get_check(payload["request_group_id"]))
    assert stored.status == "failed" and stored.lib_out_count == 0
    packages = run(
        resources.db_ops.count_query(
            Select(CheckPackage).where(CheckPackage.check_id == stored.pkid)
        )
    )
    assert packages == 0


def test_form_page_renders_without_stats_when_they_fail(client, monkeypatch, logged):
    async def stats_down():
        raise RuntimeError("stats down")

    monkeypatch.setattr(checks, "cached_stats", stats_down)
    response = client.get("/check")
    assert response.status_code == 200 and 'name="requirements"' in response.text
    assert any("stats unavailable" in m for m in logged)


def test_favicon_redirects_to_the_static_file(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 301
    assert response.headers.get("location") == "/static/favicon.ico"


def test_cancel_checks_marks_running_checks_failed(client, monkeypatch):
    async def forever(*args, **kwargs):
        await asyncio.sleep(3600)

    monkeypatch.setattr(checks, "resolve_requirements", forever)
    request_group_id = _create(client)
    run = client._loop.run_until_complete

    async def start_then_shut_down():
        checks.schedule_check(request_group_id)
        await asyncio.sleep(0.05)
        await checks.cancel_checks()

    run(start_then_shut_down())
    assert "restarted" in run(checks.get_check(request_group_id)).error


def test_finished_check_cache_is_bounded(client, monkeypatch):
    monkeypatch.setattr(checks, "FINISHED_CACHE_SIZE", 1)
    checks._finished.clear()
    run = client._loop.run_until_complete
    first = submit_and_finish(client, {"requirements": "idna", "mode": "upgrade"})
    second = submit_and_finish(client, {"requirements": "six", "mode": "upgrade"})
    for location in (first, second):
        assert run(checks.get_check_for_display(location.split("/")[-1]))
    assert list(checks._finished) == [second.split("/")[-1]]
    checks._finished.clear()


def test_user_error_message_names_the_pypi_status():
    import httpx

    request = httpx.Request("GET", "https://pypi.org/simple/x/")
    error = httpx.HTTPStatusError(
        "boom", request=request, response=httpx.Response(503, request=request)
    )
    message = checks.user_error_message(error)
    assert "HTTP 503" in message and "https://pypi.org/simple/x/" in message


def test_rate_limit_window_slides(monkeypatch):
    limits.reset()
    monkeypatch.setattr(settings, "checks_per_minute_per_ip", 1)
    now = [1000.0]
    monkeypatch.setattr(limits.time, "monotonic", lambda: now[0])
    assert limits.allow("a") and not limits.allow("a")
    now[0] += limits.WINDOW_SECONDS + 1
    assert limits.allow("a")  # the old hit has aged out
    limits.reset()


def test_static_url_for_a_missing_file_uses_version_zero():
    from src.templating import static_url

    assert static_url("no/such/file.css") == "/static/no/such/file.css?v=0"


def test_build_pypi_index_uses_a_given_cache(monkeypatch):
    monkeypatch.setattr(resources, "pypi_client", None)
    cache = MemoryCacheStore()
    index = resources.build_pypi_index(cache)
    assert index.cache is cache
    asyncio.run(resources.pypi_client.aclose())


def test_startup_on_a_migrated_file_database_survives_a_failed_sweep(
    client, monkeypatch, logged
):
    from src.settings import Settings

    async def migrated(*args, **kwargs):
        return [{"name": "alembic_version"}]

    async def sweep_fails():
        raise RuntimeError("database error: locked")

    monkeypatch.setattr(Settings, "is_memory_db", property(lambda self: False))
    monkeypatch.setattr(resources.db_ops, "read_query", migrated)
    monkeypatch.setattr(checks, "fail_stale_checks", sweep_fails)
    kept = resources.pypi_index
    monkeypatch.setattr(resources, "build_pypi_index", lambda cache=None: kept)
    client._loop.run_until_complete(resources.startup())  # must not raise
    assert any("stale-check sweep skipped" in m for m in logged)


def test_shutdown_closes_the_client_optimizes_and_disconnects(client, monkeypatch):
    import httpx

    from src.settings import Settings

    calls = []

    async def execute(statement):
        calls.append(str(statement))

    async def disconnect():
        calls.append("disconnect")

    monkeypatch.setattr(Settings, "is_memory_db", property(lambda self: False))
    monkeypatch.setattr(resources.db_ops, "execute_one", execute)
    monkeypatch.setattr(resources.async_db, "disconnect", disconnect)
    shutdown_client = httpx.AsyncClient()
    monkeypatch.setattr(resources, "pypi_client", shutdown_client)
    client._loop.run_until_complete(resources.shutdown())
    assert shutdown_client.is_closed
    assert calls == ["PRAGMA optimize", "disconnect"]


# These two run the app in a subprocess because settings are read once at
# import. Coverage can't see inside them, so db_init's file-database PRAGMAs and
# the opt-in access log show as uncovered even though these tests exercise them.


def _run_in_fresh_interpreter(script, tmp_path, *, cwd=None, **env):
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import sys; sys.path.insert(0, {str(root)!r})\n{script}",
        ],
        env={
            **os.environ,
            "LOGGING_DIRECTORY": str(tmp_path),
            "LOGGING_LEVEL": "WARNING",
            **env,
        },
        # A scratch directory has no .env, so only the variables above apply;
        # the app itself needs the repo root for its templates.
        cwd=cwd or tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout


def test_file_database_connections_use_wal_busy_timeout_and_foreign_keys(tmp_path):
    script = """
import asyncio
from sqlalchemy import text
from src.db_init import async_db

async def main():
    async with async_db.get_db_session() as session:
        values = [
            (await session.execute(text(f"PRAGMA {name}"))).scalar()
            for name in ("journal_mode", "busy_timeout", "foreign_keys", "synchronous")
        ]
    print("PRAGMAS", values)
    await async_db.disconnect()

asyncio.run(main())
"""
    out = _run_in_fresh_interpreter(
        script,
        tmp_path,
        DB_DRIVER="sqlite",
        DB_DIRECTORY=str(tmp_path),
        DB_NAME="t",
        SQLITE_BUSY_TIMEOUT_MS="7000",
    )
    assert "PRAGMAS ['wal', 7000, 1, 1]" in out  # synchronous=1 is NORMAL


def test_access_log_is_written_only_when_enabled(tmp_path):
    script = """
import os
from loguru import logger
from robyn.testing import TestClient
from src.main import app

lines = []
logger.add(lambda m: lines.append(m.record["message"]), level="INFO")
client = TestClient(app)
client.get("/about")
print("ACCESS", [line for line in lines if "/about" in line])
os._exit(0)
"""
    root = Path(__file__).resolve().parents[1]
    on = _run_in_fresh_interpreter(
        script, tmp_path, cwd=root, DB_DRIVER="memory", ACCESS_LOG="True"
    )
    assert "GET /about 200" in on
    off = _run_in_fresh_interpreter(
        script, tmp_path, cwd=root, DB_DRIVER="memory", ACCESS_LOG="False"
    )
    assert "ACCESS []" in off


def test_shutdown_after_a_failed_startup_and_on_a_memory_database(client, monkeypatch):
    # Startup can fail before the PyPI client exists, and a memory database
    # skips PRAGMA optimize; shutdown must cope with both.
    calls = []

    async def disconnect():
        calls.append("disconnect")

    async def optimize_must_not_run(statement):
        raise AssertionError("PRAGMA optimize on a memory database")

    monkeypatch.setattr(resources, "pypi_client", None)
    monkeypatch.setattr(resources.async_db, "disconnect", disconnect)
    monkeypatch.setattr(resources.db_ops, "execute_one", optimize_must_not_run)
    client._loop.run_until_complete(resources.shutdown())
    assert calls == ["disconnect"]


def test_db_driver_setting_accepts_short_names_and_rejects_typos():
    from pydantic import ValidationError

    from src.settings import DatabaseDriverEnum, Settings

    assert Settings(db_driver="SQLite").db_driver is DatabaseDriverEnum.sqlite
    assert Settings(db_driver="memory").is_memory_db
    assert Settings(db_driver=DatabaseDriverEnum.memory).is_memory_db
    with pytest.raises(ValidationError):
        Settings(db_driver="postgres")
