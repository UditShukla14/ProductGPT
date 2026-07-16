export interface HvacComponent {
  type: string
  model: string
  image_url?: string | null
}

export interface HvacAccessory {
  sku: string
  description?: string | null
  source_model?: string | null
}

export interface HvacSystem {
  id: number
  source_row_id: string | null
  ahri_number: string | null
  version: string | null
  tonnage: number | null
  seer: number | null
  eer: number | null
  hspf: number | null
  system_type: string | null
  system_type_seer2: string | null
  cond_seer: string | null
  stage: string | null
  config: string | null
  indoor_unit: string | null
  indoor_type: string | null
  furnace_btu: string | null
  cabinet_width: string | null
  coil_width: string | null
  furnace_width: string | null
  blower_type: string | null
  description: string | null
  model_status: string | null
  equipment_category: string | null
  refrigerant_type: string | null
  image_url: string | null
  outdoor_model: string | null
  coil_model: string | null
  furnace_model: string | null
  components: HvacComponent[]
  accessories?: HvacAccessory[]
  all_fields?: Record<string, string>
}

export interface HvacRecommendationRequest {
  tonnage?: number
  min_seer?: number
  max_seer?: number
  equipment_category?: string
  refrigerant_type?: string
  flow?: string
  coil_width?: string
  furnace_width?: string
  query?: string
  limit?: number
  offset?: number
  prefer_higher_seer?: boolean
}

export interface HvacRecommendation {
  system: HvacSystem
  score: number
  reason: string
}

export interface HvacRecommendationResponse {
  recommendations: HvacRecommendation[]
  meta: {
    strategy_used: string
    candidate_count: number
    total_ranked: number
    offset: number
    limit: number
    returned: number
    has_more: boolean
    filters_applied?: Record<string, unknown>
  }
}

export interface HealthResponse {
  status: string
  hvac_system_count: number
  knowledge_sources: number
  graph_node_count: number
  graph_edge_count: number
  graph_backend: string
  neo4j_connected: boolean
}

export type ComponentType = "outdoor" | "coil" | "furnace" | "auto"

export interface ComponentSearchRequest {
  model: string
  component_type?: ComponentType
  equipment_category?: string
  refrigerant_type?: string
  flow?: string
  coil_width?: string
  furnace_width?: string
  limit?: number
  offset?: number
  prefer_higher_seer?: boolean
}

export interface BoughtTogetherItem {
  type: "outdoor" | "coil" | "furnace"
  model: string
  matchup_count: number
  best_seer: number | null
  sample_system_id: number | null
  image_url?: string | null
}

export interface ComponentSearchResponse {
  query: string
  matched_type: "outdoor" | "coil" | "furnace" | null
  matched_model: string | null
  similar_matchups: HvacRecommendation[]
  bought_together: BoughtTogetherItem[]
  meta: {
    total_matchups: number
    offset: number
    limit: number
    returned: number
    has_more: boolean
    component_type: ComponentType
  }
}

export interface PairedMatchupsRequest {
  anchor_type: "outdoor" | "coil" | "furnace"
  anchor_model: string
  paired_type: "outdoor" | "coil" | "furnace"
  paired_model: string
  equipment_category?: string
  refrigerant_type?: string
  flow?: string
  coil_width?: string
  furnace_width?: string
  limit?: number
  offset?: number
  prefer_higher_seer?: boolean
}

export interface PairedMatchupsResponse {
  anchor_type: "outdoor" | "coil" | "furnace"
  anchor_model: string
  paired_type: "outdoor" | "coil" | "furnace"
  paired_model: string
  matchups: HvacRecommendation[]
  meta: {
    total_matchups: number
    offset: number
    limit: number
    returned: number
    has_more: boolean
  }
}

export interface ShopifyProductSummary {
  id: string
  title: string
  vendor?: string | null
  product_type?: string | null
  sku?: string | null
  price?: string | null
  image_url?: string | null
  status?: string | null
  handle?: string | null
}

export interface ShopifyVariantSummary {
  id?: string | null
  sku?: string | null
  title?: string | null
  price?: string | null
  inventory_quantity?: number | null
  available_for_sale?: boolean | null
}

export interface ShopifyProductDetail extends ShopifyProductSummary {
  shopify_gid?: string | null
  description?: string | null
  tags?: string[]
  inventory_quantity?: number | null
  available_for_sale?: boolean | null
  variants?: ShopifyVariantSummary[]
  created_at?: string | null
  updated_at?: string | null
}

export interface ShopifyProductSearchResponse {
  query: string
  results: ShopifyProductSummary[]
}

export interface ShopifyProductRecommendation {
  product: ShopifyProductSummary
  order_count?: number | null
  reason?: string | null
}

export interface ShopifyProductRecommendationsResponse {
  product_id: string
  items: ShopifyProductRecommendation[]
}

export interface ShopifyCategoryBrandGroup {
  vendor: string
  products: ShopifyProductSummary[]
}

export interface ShopifySameCategoryByBrandResponse {
  product_id: string
  category?: string | null
  current_vendor?: string | null
  match_keywords?: string[]
  brands: ShopifyCategoryBrandGroup[]
}

export interface ShopifySyncStatusResponse {
  products: number
  customers: number
  orders: number
  job: ShopifySyncJobStatus
}

export type ShopifySyncJobState = "idle" | "running" | "completed" | "failed"

export interface ShopifySyncJobStatus {
  state: ShopifySyncJobState
  started_at?: string | null
  finished_at?: string | null
  current_resource?: string | null
  phase?: string | null
  error?: string | null
  requested_resources?: string[]
  results?: ShopifySyncResourceResult[]
  graph_rebuilt?: boolean
}

export interface ShopifySyncResourceResult {
  resource: string
  fetched: number
  upserted: number
  details_fetched?: number
  total_in_db: number
  status: string
  error?: string | null
}

export interface ShopifySyncStartRequest {
  resources?: Array<"products" | "customers" | "orders">
  rebuild_graph?: boolean
}

export interface ShopifySyncStartResponse {
  message: string
  job: ShopifySyncJobStatus
}

export interface ChatHistoryMessage {
  role: "user" | "assistant"
  content: string
}

export interface ChatHvacCitation {
  ahri_number?: string | null
  tonnage?: number | null
  seer?: number | null
  equipment_category?: string | null
  refrigerant_type?: string | null
  outdoor_model?: string | null
  coil_model?: string | null
  furnace_model?: string | null
  reason?: string | null
  score?: number | null
}

export interface ChatShopifyCitation {
  id?: string | null
  title?: string | null
  vendor?: string | null
  product_type?: string | null
  sku?: string | null
  image_url?: string | null
  handle?: string | null
  status?: string | null
}

export interface ChatRetrievalEvent {
  tool: string
  input?: Record<string, unknown>
  preview?: {
    tool?: string
    count?: number
    items?: Array<ChatHvacCitation | ChatShopifyCitation>
    matched_model?: string | null
    matched_type?: string | null
    product?: ChatShopifyCitation
    product_id?: string
    matchup_count?: number
    bought_together_count?: number
    error?: string
  }
}

export type ChatSseHandler = {
  onToken?: (text: string) => void
  onRetrieval?: (event: ChatRetrievalEvent) => void
  onError?: (message: string) => void
  onDone?: (meta: { ok: boolean; refused?: string }) => void
}
