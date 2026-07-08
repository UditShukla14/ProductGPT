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

export function fetchShopifySameCategory(productId: string, perBrandLimit = 8) {
  const params = new URLSearchParams({ per_brand_limit: String(perBrandLimit) })
  return request<ShopifySameCategoryByBrandResponse>(
    `/shopify/products/${encodeURIComponent(productId)}/same-category?${params}`
  )
}
