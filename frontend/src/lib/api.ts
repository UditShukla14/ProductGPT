import type {
  ComponentSearchRequest,
  ComponentSearchResponse,
  HealthResponse,
  HvacRecommendationRequest,
  HvacRecommendationResponse,
  PairedMatchupsRequest,
  PairedMatchupsResponse,
  ShopifyProductDetail,
  ShopifyProductRecommendationsResponse,
  ShopifyProductSearchResponse,
  ShopifySameCategoryByBrandResponse,
  ShopifySyncStartResponse,
  ShopifySyncStatusResponse,
} from "@/types/api"

const API_BASE = "/api/v1"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    const text = await response.text()
    if (text) {
      try {
        const body = JSON.parse(text) as { detail?: unknown }
        if (body?.detail) {
          message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
        } else {
          message = text
        }
      } catch {
        message = text
      }
    }
    throw new Error(message)
  }

  return response.json() as Promise<T>
}

export function fetchHealth() {
  return request<HealthResponse>("/health")
}

export function fetchRecommendations(payload: HvacRecommendationRequest) {
  return request<HvacRecommendationResponse>("/recommendations/hvac", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function fetchComponentSearch(payload: ComponentSearchRequest) {
  return request<ComponentSearchResponse>("/hvac/components/search", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function fetchPairedMatchups(payload: PairedMatchupsRequest) {
  return request<PairedMatchupsResponse>("/hvac/components/matchups", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function searchShopifyProducts(query: string, limit = 10) {
  const params = new URLSearchParams({ q: query, limit: String(limit) })
  return request<ShopifyProductSearchResponse>(`/shopify/products/search?${params}`)
}

export function fetchShopifyProduct(productId: string) {
  return request<ShopifyProductDetail>(`/shopify/products/${encodeURIComponent(productId)}`)
}

export function fetchShopifyBoughtTogether(productId: string, limit = 8) {
  const params = new URLSearchParams({ limit: String(limit) })
  return request<ShopifyProductRecommendationsResponse>(
    `/shopify/products/${encodeURIComponent(productId)}/bought-together?${params}`
  )
}

export function fetchShopifyMatchups(
  productId: string,
  options: { limit?: number; offset?: number; prefer_higher_seer?: boolean } = {}
) {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 25),
    offset: String(options.offset ?? 0),
    prefer_higher_seer: String(options.prefer_higher_seer ?? true),
  })
  return request<ComponentSearchResponse>(
    `/shopify/products/${encodeURIComponent(productId)}/matchups?${params}`
  )
}

export function fetchShopifySameCategory(productId: string, perBrandLimit = 8) {
  const params = new URLSearchParams({ per_brand_limit: String(perBrandLimit) })
  return request<ShopifySameCategoryByBrandResponse>(
    `/shopify/products/${encodeURIComponent(productId)}/same-category?${params}`
  )
}

export function fetchShopifySyncStatus() {
  return request<ShopifySyncStatusResponse>("/shopify/sync/status")
}

export async function startShopifySync(): Promise<ShopifySyncStartResponse> {
  const response = await fetch(`${API_BASE}/shopify/sync/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })

  const text = await response.text()
  let body: ShopifySyncStartResponse & { detail?: string; message?: string; job?: ShopifySyncStartResponse["job"] }
  try {
    body = text ? (JSON.parse(text) as typeof body) : ({} as typeof body)
  } catch {
    throw new Error(text || `Request failed with status ${response.status}`)
  }

  if (response.status === 409) {
    throw new Error(body.message ?? body.detail ?? "A Shopify sync is already running")
  }

  if (!response.ok) {
    throw new Error(
      typeof body.detail === "string" ? body.detail : `Request failed with status ${response.status}`
    )
  }

  return body
}
