# -*- coding: utf-8 -*-
"""
Check lifecycle: create the row, resolve in the background, store the report.

A POST returns as soon as the row exists; the browser then polls the status
fragment. State lives in SQLite, so polling works whichever Robyn worker
process answers. A check whose process died mid-run is marked failed once it
is older than the timeout (see fail_stale_checks / is_stale).
"""

import asyncio
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

import httpx
from dsg_lib.async_database_functions.database_operations import DatabaseErrorResult
from loguru import logger
from sqlalchemy import Select, func, insert, update

from . import resources
from .db_tables import Check, CheckPackage, CheckStatus
from .resolver.environment import TargetEnvironment
from .resolver.models import ResolutionReport
from .resolver.parse import redact_credentials
from .resolver.service import resolve_requirements
from .resources import db_ops, ensure_ok
from .settings import settings

_tasks: set[asyncio.Task] = set()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _naive_utc(value: datetime) -> datetime:
    return (
        value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    )


# An accepted check touches date_updated every HEARTBEAT_SECONDS - while it
# waits for a slot and while it runs. When its process dies (a crash, a
# deploy, a dev-server reload) the heartbeat stops, and the check is reported
# failed once it misses a few, instead of the page polling forever for a
# result nobody is computing. A check whose process died before scheduling it
# never beats at all, so the same rule covers it.
HEARTBEAT_SECONDS = 10
STALE_SECONDS = 3 * HEARTBEAT_SECONDS


def _cutoff(seconds: int) -> datetime:
    return _naive_utc(utcnow() - timedelta(seconds=seconds))


def is_stale(check: Check) -> bool:
    return check.status not in CheckStatus.finished and _naive_utc(
        check.date_updated
    ) < _cutoff(STALE_SECONDS)


async def create_check(
    *,
    requirements: str,
    python_version: str,
    platform: str,
    mode: str,
    host_ip: str | None,
    user_agent: str | None,
) -> str:
    request_group_id = str(uuid.uuid4())
    lines = [
        line
        for line in requirements.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    ensure_ok(
        await db_ops.execute_one(
            insert(Check).values(
                pkid=str(uuid.uuid4()),
                request_group_id=request_group_id,
                status=CheckStatus.pending,
                target_python=python_version,
                platform=platform,
                mode=mode,
                text_in=redact_credentials(requirements),
                lib_in_count=len(lines),
                host_ip=host_ip,
                user_agent=(user_agent or "")[:512] or None,
                date_created=utcnow(),
                date_updated=utcnow(),
            )
        )
    )
    return request_group_id


def schedule_check(request_group_id: str, *, reserved: bool = False) -> asyncio.Task:
    task = asyncio.get_running_loop().create_task(
        run_check(request_group_id, reserved=reserved)
    )
    # Keep a strong reference: the loop only holds weak ones to tasks.
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return task


async def wait_for_checks() -> None:
    """Wait for every scheduled check in this process (tests, graceful shutdown)."""
    while _tasks:
        await asyncio.gather(*list(_tasks), return_exceptions=True)


async def cancel_checks() -> None:
    for task in list(_tasks):
        task.cancel()
    await asyncio.gather(*list(_tasks), return_exceptions=True)


async def get_check(request_group_id: str) -> Check | None:
    found = ensure_ok(
        await db_ops.read_one_record(
            Select(Check).where(Check.request_group_id == request_group_id)
        )
    )
    return found


# Finished checks never change again, so their rows can be served from
# memory; shared result links are the hottest read in the app.
_finished: OrderedDict[str, Check] = OrderedDict()
FINISHED_CACHE_SIZE = 256


async def get_check_for_display(request_group_id: str) -> Check | None:
    check = _finished.get(request_group_id)
    if check is not None:
        _finished.move_to_end(request_group_id)
        return check
    check = await get_check(request_group_id)
    if check is not None and check.status in CheckStatus.finished:
        _finished[request_group_id] = check
        while len(_finished) > FINISHED_CACHE_SIZE:
            _finished.popitem(last=False)
    return check


async def _set(request_group_id: str, **values) -> None:
    values.setdefault("date_updated", utcnow())
    ensure_ok(
        await db_ops.execute_one(
            update(Check)
            .where(Check.request_group_id == request_group_id)
            .values(**values)
        )
    )


# Concurrent resolutions per process. Each one holds a worker thread and
# makes many PyPI requests; past this, checks wait in "pending" (still beating).
_slots: dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = {}
# Accepted in this process and not finished yet (waiting for a slot or running).
_in_flight = 0


def _slot() -> asyncio.Semaphore:
    # One per event loop: the test client runs each test on a fresh loop.
    loop = asyncio.get_running_loop()
    if loop not in _slots:
        _slots[loop] = asyncio.Semaphore(settings.max_concurrent_checks)
    return _slots[loop]


def queue_is_full() -> bool:
    return _in_flight >= settings.max_concurrent_checks + settings.max_queued_checks


def try_reserve() -> bool:
    """Claim a place in this process's queue for a check about to be created;
    False when it's full. Tested and claimed with no await in between, so a
    burst of concurrent submissions can't all see the same free room. Pass
    reserved=True to run_check/schedule_check, which then own the claim, or
    call release_reservation() if the check is never run."""
    global _in_flight
    if queue_is_full():
        return False
    _in_flight += 1
    return True


def release_reservation() -> None:
    global _in_flight
    _in_flight -= 1


def user_error_message(exc: BaseException) -> str:
    """What a visitor sees when a check fails. PyPI/network trouble is worth
    describing; anything else is an internal error whose text (SQL, paths)
    belongs in the log only."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"PyPI returned HTTP {exc.response.status_code} for {exc.request.url}. Try again shortly."
    if isinstance(exc, httpx.HTTPError):
        return f"Could not reach PyPI ({type(exc).__name__}). Try again shortly."
    return "An internal error stopped this check. It has been logged."


async def run_check(request_group_id: str, *, reserved: bool = False) -> None:
    """Run a stored check. `reserved`: the caller already holds a queue place
    from try_reserve(); this releases it when the check ends either way."""
    global _in_flight
    if not reserved:
        _in_flight += 1
    try:
        check = await get_check(request_group_id)
        if check is None:
            logger.error(f"check {request_group_id} vanished before it ran")
            return
        heartbeat = asyncio.create_task(_heartbeat(request_group_id))
        try:
            async with _slot():
                await _resolve_and_store(check)
        except asyncio.CancelledError:
            await _set(
                request_group_id,
                status=CheckStatus.failed,
                error="The server restarted while this check was running.",
                date_finished=utcnow(),
            )
            raise
        finally:
            heartbeat.cancel()
    finally:
        release_reservation()


async def _resolve_and_store(check: Check) -> None:
    request_group_id = check.request_group_id
    started = time.monotonic()
    await _set(request_group_id, status=CheckStatus.running, date_started=utcnow())
    try:
        report = await resolve_requirements(
            check.text_in,
            index=resources.pypi_index,
            target=TargetEnvironment(check.target_python, check.platform),
            mode=check.mode,
            timeout=settings.check_timeout_seconds,
            max_rounds=settings.resolver_max_rounds,
        )
        await store_report(check, report)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception(f"check {request_group_id} failed")
        await _set(
            request_group_id,
            status=CheckStatus.failed,
            error=user_error_message(exc),
            duration_ms=int((time.monotonic() - started) * 1000),
            date_finished=utcnow(),
        )


async def _heartbeat(request_group_id: str) -> None:
    while True:
        await asyncio.sleep(HEARTBEAT_SECONDS)
        try:
            await _set(request_group_id)
        except RuntimeError as exc:  # a missed beat only risks a false "stale"
            logger.warning(f"heartbeat for {request_group_id} failed: {exc}")


async def store_report(check: Check, report: ResolutionReport) -> None:
    now = utcnow()
    statements: list[tuple] = []
    if report.packages:
        # One executemany rather than a statement per package: SQLite allows
        # one writer at a time across every worker process, and this
        # transaction was holding that lock for ~120 ms with 114 packages -
        # enough that a burst of finishing checks starved some writers past
        # the busy timeout ("database is locked").
        statements.append(
            (
                insert(CheckPackage),
                [
                    {
                        "pkid": str(uuid.uuid4()),
                        "check_id": check.pkid,
                        "name": p.name,
                        "extras": ",".join(p.extras) or None,
                        "input_spec": p.input_spec,
                        "current_version": p.current_version,
                        "latest_version": p.latest_version,
                        "latest_compatible": p.latest_compatible,
                        "resolved_version": p.resolved_version,
                        "is_direct": p.is_direct,
                        "is_held_back": p.is_held_back,
                        "held_back_by": p.held_back_by,
                        "vulnerability_count": len(p.vulnerabilities),
                        "vulnerabilities": [v.model_dump() for v in p.vulnerabilities],
                        "date_created": now,
                        "date_updated": now,
                    }
                    for p in report.packages
                ],
            )
        )
    statements.append(
        (
            update(Check)
            .where(Check.pkid == check.pkid)
            .values(
                status=CheckStatus.done if report.ok else CheckStatus.failed,
                report=report.model_dump(mode="json"),
                lib_out_count=len(report.packages),
                resolved_requirements=report.requirements_txt or None,
                locked_requirements=report.lock_txt or None,
                has_conflicts=bool(report.conflicts),
                error=report.error,
                duration_ms=report.duration_ms,
                date_finished=now,
                date_updated=now,
            ),
            None,
        )
    )
    # One transaction, so a reader never sees "done" without its packages.
    ensure_ok(await db_ops.execute_many(statements))


async def fail_stale_checks() -> None:
    """Checks left pending/running by a process that died (restart, OOM)."""
    ensure_ok(
        await db_ops.execute_one(
            update(Check)
            .where(
                Check.status.notin_(CheckStatus.finished),
                Check.date_updated < _cutoff(STALE_SECONDS),
            )
            .values(
                status=CheckStatus.failed,
                error="The server restarted while this check was running.",
            )
        )
    )


def _or_default(result, default, what: str):
    """For pages that should still render through a database hiccup: fall back
    to `default`, but log the DatabaseErrorResult rather than letting a broken
    database pass for "no checks yet"."""
    if isinstance(result, DatabaseErrorResult):
        logger.warning(f"{what} unavailable: {result.get('error')}")
        return default
    return result


async def recent_checks(limit: int = 25, offset: int = 0) -> tuple[list[Check], int]:
    query = Select(Check).order_by(Check.date_created.desc())
    total = _or_default(await db_ops.count_query(Select(Check)), 0, "check count")
    rows = _or_default(
        await db_ops.read_query(query.limit(limit).offset(offset)), [], "recent checks"
    )
    return rows, total


_stats_cache: tuple[float, dict] | None = None
STATS_CACHE_SECONDS = 30


async def cached_stats() -> dict:
    """stats() is nine aggregate queries; the form page shows a summary of it
    on every view, so reuse a result for a short while per process."""
    global _stats_cache
    now = time.monotonic()
    if _stats_cache is None or now - _stats_cache[0] > STATS_CACHE_SECONDS:
        _stats_cache = (now, await stats())
    return _stats_cache[1]


async def stats() -> dict:
    def scalar_rows(result) -> list[tuple]:
        # read_query returns a dict per row for multi-column selects.
        rows = ensure_ok(result)
        return [
            tuple(row.values()) if isinstance(row, dict) else tuple(row) for row in rows
        ]

    total_checks = await db_ops.count_query(Select(Check))
    done_checks = await db_ops.count_query(
        Select(Check).where(Check.status == CheckStatus.done)
    )
    conflict_checks = await db_ops.count_query(
        Select(Check).where(Check.has_conflicts.is_(True))
    )
    total_packages = await db_ops.count_query(Select(CheckPackage.name).distinct())
    by_python = scalar_rows(
        await db_ops.read_query(
            Select(Check.target_python, func.count(Check.pkid))
            .group_by(Check.target_python)
            .order_by(Check.target_python)
        )
    )
    top_packages = scalar_rows(
        await db_ops.read_query(
            Select(CheckPackage.name, func.count(CheckPackage.pkid).label("n"))
            # Only names PyPI knows: latest_version is null for a package the
            # index doesn't have, so a pasted private/internal name (or one
            # whose lookup failed) never appears on this public page.
            .where(
                CheckPackage.is_direct.is_(True),
                CheckPackage.latest_version.isnot(None),
            )
            .group_by(CheckPackage.name)
            .order_by(func.count(CheckPackage.pkid).desc())
            .limit(15)
        )
    )
    top_held_back = scalar_rows(
        await db_ops.read_query(
            Select(CheckPackage.name, func.count(CheckPackage.pkid).label("n"))
            .where(CheckPackage.is_held_back.is_(True))
            .group_by(CheckPackage.name)
            .order_by(func.count(CheckPackage.pkid).desc())
            .limit(10)
        )
    )
    top_vulnerable = scalar_rows(
        await db_ops.read_query(
            Select(
                CheckPackage.name,
                CheckPackage.resolved_version,
                func.count(CheckPackage.pkid).label("n"),
            )
            .where(CheckPackage.vulnerability_count > 0)
            .group_by(CheckPackage.name, CheckPackage.resolved_version)
            .order_by(func.count(CheckPackage.pkid).desc())
            .limit(10)
        )
    )
    avg_duration = _or_default(
        await db_ops.read_one_record(
            Select(func.avg(Check.duration_ms)).where(Check.status == CheckStatus.done)
        ),
        None,
        "average duration",
    )

    def count(value) -> int:
        value = _or_default(value, 0, "a stats count")
        return value if isinstance(value, int) else 0

    return {
        "total_checks": count(total_checks),
        "done_checks": count(done_checks),
        "conflict_checks": count(conflict_checks),
        "distinct_packages": count(total_packages),
        "avg_duration_ms": (
            int(avg_duration) if isinstance(avg_duration, (int, float)) else 0
        ),
        "by_python": [(row[0], row[1]) for row in by_python],
        "top_packages": [(row[0], row[1]) for row in top_packages],
        "top_held_back": [(row[0], row[1]) for row in top_held_back],
        "top_vulnerable": [(row[0], row[1], row[2]) for row in top_vulnerable],
    }
