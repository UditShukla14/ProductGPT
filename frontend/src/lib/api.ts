import type {
  ComponentSearchRequest,
  ComponentSearchResponse,
  ChatHistoryMessage,
  ChatRetrievalEvent,
  ChatSseHandler,
  HealthResponse,
  HvacRecommendationRequest,
  HvacRecommendationResponse,
  PairedMatchupsRequest,
  PairedMatchupsResponse,
  ShopifyProductDetail,
  ShopifyProductRecommendationsResponse,
  ShopifyProductSearchResponse,
  ShopifySameCategoryByBrandResponse,
  ShopifySyncStartRequest,
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

export async function startShopifySync(
  payload: ShopifySyncStartRequest = {}
): Promise<ShopifySyncStartResponse> {
  const response = await fetch(`${API_BASE}/shopify/sync/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      resources: payload.resources,
      rebuild_graph: payload.rebuild_graph ?? true,
    }),
  })

  const text = await response.text()
  let body: ShopifySyncStartResponse & {
    detail?: string
    message?: string
    job?: ShopifySyncStartResponse["job"]
  }
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

function parseSseChunk(
  buffer: string,
  onEvent: (event: string, data: string) => void
): string {
  const parts = buffer.split("\n\n")
  const rest = parts.pop() ?? ""
  for (const part of parts) {
    if (!part.trim()) continue
    let eventName = "message"
    const dataLines: string[] = []
    for (const line of part.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim())
      }
    }
    if (dataLines.length) {
      onEvent(eventName, dataLines.join("\n"))
    }
  }
  return rest
}

export async function streamChatMessage(
  payload: { message: string; productId: string; history?: ChatHistoryMessage[] },
  handlers: ChatSseHandler,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE}/chat/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: payload.message,
      product_id: payload.productId,
      history: payload.history ?? [],
    }),
    signal,
  })

  if (!response.ok) {
    const text = await response.text()
    let message = `Request failed with status ${response.status}`
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

  if (!response.body) {
    throw new Error("Chat response had no body")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  const handleEvent = (event: string, data: string) => {
    let parsed: Record<string, unknown> = {}
    try {
      parsed = JSON.parse(data) as Record<string, unknown>
    } catch {
      return
    }

    if (event === "token" && typeof parsed.text === "string") {
      handlers.onToken?.(parsed.text)
    } else if (event === "retrieval") {
      handlers.onRetrieval?.(parsed as unknown as ChatRetrievalEvent)
    } else if (event === "error" && typeof parsed.message === "string") {
      handlers.onError?.(parsed.message)
    } else if (event === "done") {
      handlers.onDone?.({
        ok: Boolean(parsed.ok),
        refused: typeof parsed.refused === "string" ? parsed.refused : undefined,
      })
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    buffer = parseSseChunk(buffer, handleEvent)
  }
  if (buffer.trim()) {
    parseSseChunk(buffer + "\n\n", handleEvent)
  }
}
