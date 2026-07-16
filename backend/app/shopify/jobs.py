"""Background Shopify sync job state (runs in a server thread, survives client disconnect)."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Sequence

from app.shopify import ALL_RESOURCES
from app.shopify.client import ResourceName
from app.shopify.graph.store import shopify_graph_store
from app.shopify.service import build_shopify_client, is_shopify_configured
from app.shopify.sync import ResourceSyncResult, sync_resources

logger = logging.getLogger(__name__)

JobState = Literal["idle", "running", "completed", "failed"]


@dataclass
class ShopifySyncJob:
    state: JobState = "idle"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    current_resource: str | None = None
    phase: str | None = None
    error: str | None = None
    requested_resources: list[str] = field(default_factory=list)
    results: list[ResourceSyncResult] = field(default_factory=list)
    graph_rebuilt: bool = False
    graph_stats: dict[str, Any] | None = None


_lock = threading.Lock()
_job = ShopifySyncJob()
_thread: threading.Thread | None = None


def get_sync_job() -> ShopifySyncJob:
    with _lock:
        return ShopifySyncJob(
            state=_job.state,
            started_at=_job.started_at,
            finished_at=_job.finished_at,
            current_resource=_job.current_resource,
            phase=_job.phase,
            error=_job.error,
            requested_resources=list(_job.requested_resources),
            results=list(_job.results),
            graph_rebuilt=_job.graph_rebuilt,
            graph_stats=dict(_job.graph_stats) if _job.graph_stats else None,
        )


def is_sync_running() -> bool:
    with _lock:
        return _job.state == "running"


def _normalize_resources(
    resources: Sequence[ResourceName] | None,
) -> tuple[ResourceName, ...]:
    if not resources:
        return ALL_RESOURCES
    unique: list[ResourceName] = []
    seen: set[str] = set()
    for name in resources:
        if name not in ALL_RESOURCES:
            raise ValueError(f"Unsupported Shopify resource: {name}")
        if name in seen:
            continue
        seen.add(name)
        unique.append(name)
    # Keep stable ALL_RESOURCES order
    return tuple(name for name in ALL_RESOURCES if name in seen)


def start_sync_job(
    *,
    resources: Sequence[ResourceName] | None = None,
    rebuild_graph: bool = True,
) -> ShopifySyncJob:
    global _thread

    selected = _normalize_resources(resources)

    with _lock:
        if _job.state == "running":
            raise RuntimeError("A Shopify sync is already running on the server")

        if not is_shopify_configured():
            raise RuntimeError(
                "Shopify API is not configured. Set SHOPIFY_API_BASE_URL, "
                "SHOPIFY_API_TOKEN, and SHOPIFY_API_SHOP_DOMAIN."
            )

        _job.state = "running"
        _job.started_at = datetime.now(timezone.utc)
        _job.finished_at = None
        _job.current_resource = None
        _job.phase = "starting"
        _job.error = None
        _job.requested_resources = list(selected)
        _job.results = []
        _job.graph_rebuilt = False
        _job.graph_stats = None

    _thread = threading.Thread(
        target=_run_sync_job,
        kwargs={"resources": selected, "rebuild_graph": rebuild_graph},
        name="shopify-sync",
        daemon=True,
    )
    _thread.start()
    return get_sync_job()


def _set_job(**updates: Any) -> None:
    with _lock:
        for key, value in updates.items():
            setattr(_job, key, value)


def _on_resource_start(resource: str) -> None:
    _set_job(current_resource=resource, phase="syncing")


def _run_sync_job(*, resources: tuple[ResourceName, ...], rebuild_graph: bool) -> None:
    results: list[ResourceSyncResult] = []
    try:
        logger.info(
            "Background Shopify sync started (resources=%s, rebuild_graph=%s)",
            ",".join(resources),
            rebuild_graph,
        )
        with build_shopify_client() as client:
            results = sync_resources(
                client,
                resources,
                rebuild_graph=False,
                on_resource_start=_on_resource_start,
            )

        if rebuild_graph and all(result.status == "completed" for result in results):
            _set_job(phase="rebuilding_graph", current_resource=None)
            stats = shopify_graph_store.rebuild()
            graph_stats = stats.model_dump()
            graph_rebuilt = True
        else:
            graph_stats = (
                shopify_graph_store.get_stats().model_dump()
                if shopify_graph_store.is_ready
                else None
            )
            graph_rebuilt = False

        failed = [result for result in results if result.status != "completed"]
        if failed:
            error = "; ".join(
                f"{result.resource}: {result.error or 'sync failed'}" for result in failed
            )
            _set_job(
                state="failed",
                finished_at=datetime.now(timezone.utc),
                phase=None,
                current_resource=None,
                results=results,
                error=error,
                graph_rebuilt=graph_rebuilt,
                graph_stats=graph_stats,
            )
            logger.error("Background Shopify sync finished with errors: %s", error)
            return

        _set_job(
            state="completed",
            finished_at=datetime.now(timezone.utc),
            phase=None,
            current_resource=None,
            results=results,
            graph_rebuilt=graph_rebuilt,
            graph_stats=graph_stats,
        )
        logger.info("Background Shopify sync completed successfully")
    except Exception as exc:
        logger.exception("Background Shopify sync failed")
        _set_job(
            state="failed",
            finished_at=datetime.now(timezone.utc),
            phase=None,
            current_resource=None,
            results=results,
            error=str(exc),
        )
