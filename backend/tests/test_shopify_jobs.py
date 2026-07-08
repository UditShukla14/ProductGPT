"""Tests for background Shopify sync jobs."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.shopify.jobs import get_sync_job, is_sync_running, start_sync_job
from app.shopify.storage import upsert_records


@pytest.fixture
def shopify_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.shopify.storage.SHOPIFY_DATA_DIR", tmp_path)
    monkeypatch.setattr("app.shopify.storage._engines", {})
    monkeypatch.setattr("app.shopify.storage._sessions", {})
    monkeypatch.setattr("app.config.settings.shopify_api_base_url", "https://shop.worxstream.io/api/v1")
    monkeypatch.setattr("app.config.settings.shopify_api_token", "test-token")
    monkeypatch.setattr("app.config.settings.shopify_api_shop_domain", "example.myshopify.com")
    monkeypatch.setattr("app.config.settings.shopify_enrich_details", False)
    monkeypatch.setattr("app.shopify.jobs._job.state", "idle")
    monkeypatch.setattr("app.shopify.jobs._job.results", [])
    monkeypatch.setattr("app.shopify.jobs._job.error", None)
    return tmp_path


def test_start_sync_job_runs_in_background(shopify_env, monkeypatch):
    calls: list[str] = []

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def iter_resource(self, resource):
            if resource == "products":
                yield {"id": "p1", "title": "Product 1"}
            elif resource == "customers":
                yield {"id": "c1", "email": "a@example.com"}
            elif resource == "orders":
                yield {"id": "o1", "name": "#1001"}

    def fake_sync_resources(client, resources, **kwargs):
        on_start = kwargs.get("on_resource_start")
        results = []
        for resource in resources:
            if on_start:
                on_start(resource)
            calls.append(resource)
            for item in client.iter_resource(resource):
                upsert_records(resource, [item])
            from app.shopify.sync import ResourceSyncResult
            from app.shopify.storage import count_records

            results.append(
                ResourceSyncResult(
                    resource=resource,
                    fetched=1,
                    upserted=1,
                    total_in_db=count_records(resource),
                    status="completed",
                )
            )
        return results

    monkeypatch.setattr("app.shopify.jobs.build_shopify_client", lambda: FakeClient())
    monkeypatch.setattr("app.shopify.jobs.sync_resources", fake_sync_resources)
    monkeypatch.setattr(
        "app.shopify.jobs.shopify_graph_store.rebuild",
        lambda: type("Stats", (), {"model_dump": lambda self: {"node_count": 1, "edge_count": 0, "nodes_by_type": {}, "edges_by_type": {}, "product_count": 1, "customer_count": 1, "order_count": 1}})(),
    )

    job = start_sync_job(rebuild_graph=True)
    assert job.state == "running"

    deadline = time.time() + 5
    while time.time() < deadline:
        if get_sync_job().state in {"completed", "failed"}:
            break
        time.sleep(0.05)

    final = get_sync_job()
    assert final.state == "completed"
    assert calls == ["products", "customers", "orders"]
    assert final.graph_rebuilt is True
    assert not is_sync_running()


def test_start_sync_job_rejects_when_already_running(shopify_env, monkeypatch):
    monkeypatch.setattr("app.shopify.jobs._job.state", "running")
    with pytest.raises(RuntimeError, match="already running"):
        start_sync_job()
