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

export function componentTypeLabel(type: ComponentType | null | undefined): string {
  if (!type || type === "auto") return "component"
  return COMPONENT_TYPE_LABELS[type]
}

export function componentTypePlaceholder(type: ComponentType): string {
  return (
    COMPONENT_TYPE_OPTIONS.find((option) => option.value === type)?.placeholder ??
    COMPONENT_TYPE_OPTIONS[0].placeholder
  )
}
