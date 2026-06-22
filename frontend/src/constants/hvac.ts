import type { ComponentType } from "@/types/api"

/** Equipment categories from Goodman November Ratings export */
export const EQUIPMENT_CATEGORY_OPTIONS = [
  "AC",
  "Heat Pump",
  "Package AC",
  "Package Heat Pump",
] as const

/** Refrigerant types from Goodman November Ratings export */
export const REFRIGERANT_OPTIONS = ["R-32", "R-410A"] as const

export const DEFAULT_REFRIGERANT = "R-32" as const

/** Coil / air-handler flow from Goodman Coil Type field */
export const FLOW_OPTIONS = ["Horizontal", "Vertical"] as const

/** Coil cabinet widths parsed from Goodman coil model numbers */
export const COIL_WIDTH_OPTIONS = ["18", "22", "26", "30"] as const

/** Furnace cabinet widths from Goodman Shopify cabinet_width metafield */
export const FURNACE_WIDTH_OPTIONS = ["14", "17.5", "21", "24.5"] as const

export function formatWidthInches(width: string): string {
  return `${width}"`
}

export function isHeatPumpCategory(category?: string | null): boolean {
  return category === "Heat Pump" || category === "Package Heat Pump"
}

export function componentTypeOrder(
  equipmentCategory?: string | null
): Array<"outdoor" | "coil" | "furnace"> {
  return isHeatPumpCategory(equipmentCategory)
    ? ["coil", "outdoor", "furnace"]
    : ["outdoor", "coil", "furnace"]
}

export function componentTypeOptionsForCategory(equipmentCategory?: string | null) {
  if (!isHeatPumpCategory(equipmentCategory)) {
    return COMPONENT_TYPE_OPTIONS
  }

  const byValue = Object.fromEntries(
    COMPONENT_TYPE_OPTIONS.map((option) => [option.value, option])
  ) as Record<ComponentType, (typeof COMPONENT_TYPE_OPTIONS)[number]>

  return [
    byValue.auto,
    {
      ...byValue.coil,
      label: "Air handler",
      placeholder: "Air handler model — e.g. CHPTA3630B3",
    },
    {
      ...byValue.outdoor,
      label: "Heat pump (outdoor unit)",
      placeholder: "Outdoor heat pump model — e.g. GLXS3BN2410A",
    },
    byValue.furnace,
  ]
}

/** Goodman AHRI field names mapped to search component types */
export const COMPONENT_TYPE_OPTIONS: Array<{
  value: ComponentType
  label: string
  placeholder: string
}> = [
  {
    value: "auto",
    label: "Auto-detect",
    placeholder: "Condenser, evaporator coil, or furnace — e.g. GLXS3BN2410A",
  },
  {
    value: "outdoor",
    label: "Condenser (outdoor unit)",
    placeholder: "Outdoor unit model — e.g. GLXS3BN2410A",
  },
  {
    value: "coil",
    label: "Evaporator coil / air handler",
    placeholder: "Indoor coil or air handler — e.g. (C,M,V)CG30P(A,B,C)2M+TXV",
  },
  {
    value: "furnace",
    label: "Furnace",
    placeholder: "Furnace model — e.g. GM9C800803B",
  },
]

export const COMPONENT_TYPE_LABELS: Record<"outdoor" | "coil" | "furnace", string> = {
  outdoor: "Condenser (outdoor unit)",
  coil: "Evaporator coil / air handler",
  furnace: "Furnace",
}

export const COMPONENT_SECTION_CONFIG = {
  outdoor: {
    label: "Condensers (outdoor units)",
    description: "Compatible outdoor units certified with your search",
  },
  coil: {
    label: "Evaporator coils / air handlers",
    description: "Compatible indoor coils and air handlers to complete the matchup",
  },
  furnace: {
    label: "Furnaces",
    description: "Compatible furnaces to complete the matchup",
  },
} as const

export function componentSectionConfig(
  type: "outdoor" | "coil" | "furnace",
  equipmentCategory?: string | null
) {
  if (isHeatPumpCategory(equipmentCategory)) {
    if (type === "coil") {
      return {
        label: "Air handlers",
        description: "Compatible air handlers certified with your search",
      }
    }
    if (type === "outdoor") {
      return {
        label: "Heat pumps (outdoor units)",
        description: "Compatible outdoor heat pumps to complete the matchup",
      }
    }
  }

  return COMPONENT_SECTION_CONFIG[type]
}

export function componentTypeLabel(
  type: ComponentType | null | undefined,
  equipmentCategory?: string | null
): string {
  if (!type || type === "auto") return "component"
  if (isHeatPumpCategory(equipmentCategory)) {
    if (type === "coil") return "Air handler"
    if (type === "outdoor") return "Heat pump (outdoor unit)"
  }
  return COMPONENT_TYPE_LABELS[type]
}

export function componentTypePlaceholder(
  type: ComponentType,
  equipmentCategory?: string | null
): string {
  return (
    componentTypeOptionsForCategory(equipmentCategory).find((option) => option.value === type)
      ?.placeholder ?? COMPONENT_TYPE_OPTIONS[0].placeholder
  )
}
