export interface HvacComponent {
  type: string
  model: string
  image_url?: string | null
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
  all_fields?: Record<string, string>
}

export interface HvacRecommendationRequest {
  tonnage?: number
  min_seer?: number
  max_seer?: number
  equipment_category?: string
  refrigerant_type?: string
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
