"""HTTP client for the Worxstream Shopify REST API with cursor pagination and rate limiting."""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any, Iterator, Literal

import httpx

logger = logging.getLogger(__name__)

ResourceName = Literal["products", "customers", "orders"]


class ShopifyApiError(RuntimeError):
    pass


class ShopifyAuthError(ShopifyApiError):
    pass


def normalize_bearer_token(token: str) -> str:
    value = token.strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    return value


def normalize_shop_domain(shop_domain: str) -> str:
    value = shop_domain.strip()
    if value.startswith("https://"):
        value = value[8:]
    if value.startswith("http://"):
        value = value[7:]
    return value.rstrip("/")


class ShopifyApiClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        shop_domain: str,
        *,
        page_limit: int = 0,
        requests_per_minute: int = 100,
        timeout_seconds: float = 60.0,
        max_retries: int = 5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = normalize_bearer_token(token)
        self.shop_domain = normalize_shop_domain(shop_domain)
        self.page_limit = page_limit
        self.requests_per_minute = requests_per_minute
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._request_times: deque[float] = deque()
        if not self.token:
            raise ValueError("Shopify API token is required (SHOPIFY_API_TOKEN)")
        if not self.shop_domain:
            raise ValueError("Shop domain is required (SHOPIFY_API_SHOP_DOMAIN)")
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds, connect=min(15.0, timeout_seconds)),
            headers=self._headers(),
        )

    def __enter__(self) -> ShopifyApiClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Shop-Domain": self.shop_domain,
        }

    def verify_connection(self) -> dict[str, Any]:
        """Test API auth by fetching the first products page."""
        payload = self.fetch_page("products")
        items = extract_list_items("products", payload)
        pagination = payload.get("pagination") or {}
        return {
            "ok": True,
            "shop_domain": self.shop_domain,
            "sample_count": len(items),
            "has_next_page": bool(pagination.get("has_next_page")),
        }

    def _wait_for_rate_limit(self) -> None:
        now = time.monotonic()
        window_start = now - 60.0
        while self._request_times and self._request_times[0] < window_start:
            self._request_times.popleft()

        if len(self._request_times) >= self.requests_per_minute:
            sleep_for = 60.0 - (now - self._request_times[0]) + 0.05
            if sleep_for > 0:
                logger.debug("Rate limit reached; sleeping %.2fs", sleep_for)
                time.sleep(sleep_for)
            self._wait_for_rate_limit()
            return

    def _record_request(self) -> None:
        self._request_times.append(time.monotonic())

    def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        attempt = 0

        while True:
            self._wait_for_rate_limit()
            self._record_request()
            try:
                response = self._client.request(
                    method,
                    url,
                    params=params,
                )
            except httpx.ConnectError as exc:
                host = httpx.URL(self.base_url).host or self.base_url
                raise RuntimeError(
                    f"Could not connect to Shopify API at {host}. "
                    "Check SHOPIFY_API_BASE_URL and network access."
                ) from exc
            except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout, httpx.ConnectTimeout) as exc:
                attempt += 1
                if attempt > self.max_retries:
                    raise RuntimeError(
                        f"Shopify API timed out after {self.max_retries} retries: {method} {url}"
                    ) from exc
                sleep_for = min(2**attempt, 30)
                logger.warning(
                    "Shopify API timeout (%s) on %s %s; retrying in %.1fs (%s/%s)",
                    type(exc).__name__,
                    method,
                    path,
                    sleep_for,
                    attempt,
                    self.max_retries,
                )
                time.sleep(sleep_for)
                continue

            if response.status_code == 401:
                raise ShopifyAuthError(
                    "Shopify API rejected credentials. Verify SHOPIFY_API_TOKEN "
                    f"(Authorization: Bearer) and SHOPIFY_API_SHOP_DOMAIN "
                    f"(X-Shop-Domain: {self.shop_domain}) in backend/.env"
                )

            if response.status_code == 403:
                detail = _extract_error_message(response)
                raise ShopifyAuthError(
                    f"Shopify API access denied for shop '{self.shop_domain}'. {detail}"
                )

            if response.status_code == 429:
                attempt += 1
                if attempt > self.max_retries:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                sleep_for = float(retry_after) if retry_after else min(2**attempt, 30)
                logger.warning("Shopify API rate limited (429); retrying in %.1fs", sleep_for)
                time.sleep(sleep_for)
                continue

            if response.status_code >= 500:
                attempt += 1
                if attempt > self.max_retries:
                    response.raise_for_status()
                sleep_for = min(2**attempt, 30)
                logger.warning(
                    "Shopify API server error (%s); retrying in %.1fs",
                    response.status_code,
                    sleep_for,
                )
                time.sleep(sleep_for)
                continue

            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise RuntimeError(f"Expected JSON object from {url}, got {type(payload).__name__}")
            _validate_success(payload)
            return payload

    def fetch_page(
        self,
        resource: ResourceName,
        *,
        after: str | None = None,
        resource_id: str | None = None,
    ) -> dict[str, Any]:
        if resource_id:
            return self._request("GET", f"/{resource}/{resource_id}")

        params: dict[str, Any] = {}
        if self.page_limit > 0:
            params["limit"] = self.page_limit
        if after:
            params["after"] = after
        return self._request("GET", f"/{resource}", params=params or None)

    def iter_resource(self, resource: ResourceName) -> Iterator[dict[str, Any]]:
        after: str | None = None
        page = 0
        total = 0
        while True:
            page += 1
            payload = self.fetch_page(resource, after=after)
            items = extract_list_items(resource, payload)
            total += len(items)
            pagination = payload.get("pagination") or {}
            logger.info(
                "Shopify %s page %s: %s items (%s total so far, has_next=%s)",
                resource,
                page,
                len(items),
                total,
                pagination.get("has_next_page", False),
            )
            yield from items

            if not pagination.get("has_next_page"):
                break
            after = pagination.get("end_cursor")
            if not after:
                break
        logger.info("Shopify %s pagination complete: %s records", resource, total)

    def fetch_detail(self, resource: ResourceName, resource_id: str) -> dict[str, Any]:
        payload = self.fetch_page(resource, resource_id=resource_id)
        return extract_single_item(payload)


def _validate_success(payload: dict[str, Any]) -> None:
    if payload.get("success") is False:
        message = payload.get("message") or "Shopify API request failed"
        raise ShopifyApiError(str(message))


def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            message = payload.get("message")
            if message:
                return str(message)
    except ValueError:
        pass
    return response.text[:300] or f"HTTP {response.status_code}"


def extract_list_items(resource: ResourceName, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Worxstream list envelope: { success, data: [...], pagination }."""
    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    for key in (resource, "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return []


def extract_single_item(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse Worxstream single-resource envelope: { success, data: { ... } }."""
    data = payload.get("data")
    if isinstance(data, dict):
        return data

    for key in ("product", "customer", "order"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value

    return payload
