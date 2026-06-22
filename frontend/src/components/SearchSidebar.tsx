import { Loader2, Search, Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import {
  COIL_WIDTH_OPTIONS,
  EQUIPMENT_CATEGORY_OPTIONS,
  FLOW_OPTIONS,
  FURNACE_WIDTH_OPTIONS,
  REFRIGERANT_OPTIONS,
  componentTypeOptionsForCategory,
  componentTypePlaceholder,
  formatWidthInches,
} from "@/constants/hvac"
import type { ComponentType, HvacRecommendationRequest } from "@/types/api"

export type SidebarSearchMode = "criteria" | "product"

type CriteriaForm = Omit<HvacRecommendationRequest, "limit" | "offset">

type ProductForm = {
  model: string
  component_type: ComponentType
  equipment_category?: string
  refrigerant_type?: string
  flow?: string
  coil_width?: string
  furnace_width?: string
  prefer_higher_seer: boolean
}

interface SearchSidebarProps {
  sidebarMode: SidebarSearchMode
  onSidebarModeChange: (mode: SidebarSearchMode) => void
  criteriaForm: CriteriaForm
  productForm: ProductForm
  isCriteriaLoading: boolean
  isProductLoading: boolean
  onCriteriaFieldChange: <K extends keyof CriteriaForm>(key: K, value: CriteriaForm[K]) => void
  onProductFieldChange: <K extends keyof ProductForm>(key: K, value: ProductForm[K]) => void
  onProductComponentTypeChange: (value: ComponentType) => void
  onCriteriaSubmit: (event: React.FormEvent) => void
  onProductSubmit: (event: React.FormEvent) => void
}

export function SearchSidebar({
  sidebarMode,
  onSidebarModeChange,
  criteriaForm,
  productForm,
  isCriteriaLoading,
  isProductLoading,
  onCriteriaFieldChange,
  onProductFieldChange,
  onProductComponentTypeChange,
  onCriteriaSubmit,
  onProductSubmit,
}: SearchSidebarProps) {
  const showCoilWidth = productForm.component_type === "coil"
  const showFurnaceWidth = productForm.component_type === "furnace"

  return (
    <Card className="gap-0 py-0 shadow-none">
      <CardHeader className="gap-2 px-4 py-3">
        <CardTitle className="flex items-center gap-1.5 text-sm">
          <Search className="size-3.5" />
          Search
        </CardTitle>
        <div className="flex items-center justify-between gap-2 rounded-md border bg-muted/30 px-2.5 py-2">
          <Label
            htmlFor="search_mode_toggle"
            className={`text-xs ${sidebarMode === "criteria" ? "font-medium text-foreground" : "text-muted-foreground"}`}
          >
            Requirements
          </Label>
          <Switch
            id="search_mode_toggle"
            checked={sidebarMode === "product"}
            onCheckedChange={(checked) => onSidebarModeChange(checked ? "product" : "criteria")}
            aria-label="Toggle between requirements and model number search"
          />
          <Label
            htmlFor="search_mode_toggle"
            className={`text-xs ${sidebarMode === "product" ? "font-medium text-foreground" : "text-muted-foreground"}`}
          >
            Model number
          </Label>
        </div>
      </CardHeader>

      <CardContent className="px-4 pb-4">
        {sidebarMode === "criteria" ? (
          <form className="space-y-3" onSubmit={onCriteriaSubmit}>
            <div className="grid grid-cols-2 gap-2">
              <div className="col-span-2 space-y-1">
                <Label htmlFor="tonnage" className="text-[11px] text-muted-foreground">
                  Tonnage
                </Label>
                <Select
                  id="tonnage"
                  value={String(criteriaForm.tonnage ?? "")}
                  onChange={(event) =>
                    onCriteriaFieldChange("tonnage", Number(event.target.value) || undefined)
                  }
                  className="h-8 text-sm"
                >
                  <option value="">Any</option>
                  {[1.5, 2, 2.5, 3, 3.5, 4, 5].map((value) => (
                    <option key={value} value={value}>
                      {value} Ton
                    </option>
                  ))}
                </Select>
              </div>

              <div className="space-y-1">
                <Label htmlFor="min_seer" className="text-[11px] text-muted-foreground">
                  Min SEER
                </Label>
                <Input
                  id="min_seer"
                  type="number"
                  step="0.1"
                  min={0}
                  placeholder="15"
                  value={criteriaForm.min_seer ?? ""}
                  onChange={(event) =>
                    onCriteriaFieldChange("min_seer", Number(event.target.value) || undefined)
                  }
                  className="h-8 text-sm"
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="max_seer" className="text-[11px] text-muted-foreground">
                  Max SEER
                </Label>
                <Input
                  id="max_seer"
                  type="number"
                  step="0.1"
                  min={0}
                  placeholder="Any"
                  value={criteriaForm.max_seer ?? ""}
                  onChange={(event) =>
                    onCriteriaFieldChange("max_seer", Number(event.target.value) || undefined)
                  }
                  className="h-8 text-sm"
                />
              </div>

              <div className="col-span-2 space-y-1">
                <Label htmlFor="equipment_category" className="text-[11px] text-muted-foreground">
                  Category
                </Label>
                <Select
                  id="equipment_category"
                  value={criteriaForm.equipment_category ?? ""}
                  onChange={(event) =>
                    onCriteriaFieldChange("equipment_category", event.target.value || undefined)
                  }
                  className="h-8 text-sm"
                >
                  <option value="">Any</option>
                  {EQUIPMENT_CATEGORY_OPTIONS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="col-span-2 space-y-1">
                <Label htmlFor="refrigerant_type" className="text-[11px] text-muted-foreground">
                  Refrigerant
                </Label>
                <Select
                  id="refrigerant_type"
                  value={criteriaForm.refrigerant_type ?? ""}
                  onChange={(event) =>
                    onCriteriaFieldChange("refrigerant_type", event.target.value || undefined)
                  }
                  className="h-8 text-sm"
                >
                  <option value="">Any</option>
                  {REFRIGERANT_OPTIONS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="col-span-2 space-y-1">
                <Label htmlFor="flow" className="text-[11px] text-muted-foreground">
                  Flow
                </Label>
                <Select
                  id="flow"
                  value={criteriaForm.flow ?? ""}
                  onChange={(event) =>
                    onCriteriaFieldChange("flow", event.target.value || undefined)
                  }
                  className="h-8 text-sm"
                >
                  <option value="">Any</option>
                  {FLOW_OPTIONS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="space-y-1">
                <Label htmlFor="coil_width" className="text-[11px] text-muted-foreground">
                  Coil width
                </Label>
                <Select
                  id="coil_width"
                  value={criteriaForm.coil_width ?? ""}
                  onChange={(event) =>
                    onCriteriaFieldChange("coil_width", event.target.value || undefined)
                  }
                  className="h-8 text-sm"
                >
                  <option value="">Any</option>
                  {COIL_WIDTH_OPTIONS.map((value) => (
                    <option key={value} value={value}>
                      {formatWidthInches(value)}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="space-y-1">
                <Label htmlFor="furnace_width" className="text-[11px] text-muted-foreground">
                  Furnace width
                </Label>
                <Select
                  id="furnace_width"
                  value={criteriaForm.furnace_width ?? ""}
                  onChange={(event) =>
                    onCriteriaFieldChange("furnace_width", event.target.value || undefined)
                  }
                  className="h-8 text-sm"
                >
                  <option value="">Any</option>
                  {FURNACE_WIDTH_OPTIONS.map((value) => (
                    <option key={value} value={value}>
                      {formatWidthInches(value)}
                    </option>
                  ))}
                </Select>
              </div>
            </div>

            <div className="space-y-1">
              <Label htmlFor="query" className="text-[11px] text-muted-foreground">
                Search hint
              </Label>
              <Input
                id="query"
                placeholder="modulating, ECM…"
                value={criteriaForm.query ?? ""}
                onChange={(event) =>
                  onCriteriaFieldChange("query", event.target.value || undefined)
                }
                className="h-8 text-sm"
              />
            </div>

            <div className="flex items-center justify-between rounded-md border px-2.5 py-1.5">
              <Label htmlFor="criteria_prefer_seer" className="text-xs">
                Prefer higher SEER
              </Label>
              <Switch
                id="criteria_prefer_seer"
                checked={criteriaForm.prefer_higher_seer ?? true}
                onCheckedChange={(checked) => onCriteriaFieldChange("prefer_higher_seer", checked)}
              />
            </div>

            <Button type="submit" size="sm" className="h-8 w-full" disabled={isCriteriaLoading}>
              {isCriteriaLoading ? (
                <>
                  <Loader2 className="animate-spin" />
                  Finding…
                </>
              ) : (
                <>
                  <Sparkles />
                  Recommend
                </>
              )}
            </Button>
          </form>
        ) : (
          <form className="space-y-3" onSubmit={onProductSubmit}>
            <div className="space-y-1">
              <Label htmlFor="product_model" className="text-[11px] text-muted-foreground">
                Model number
              </Label>
              <Input
                id="product_model"
                placeholder={componentTypePlaceholder(
                  productForm.component_type,
                  productForm.equipment_category
                )}
                value={productForm.model}
                onChange={(event) => onProductFieldChange("model", event.target.value)}
                className="h-8 text-sm"
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="component_type" className="text-[11px] text-muted-foreground">
                Component
              </Label>
              <Select
                id="component_type"
                value={productForm.component_type}
                onChange={(event) =>
                  onProductComponentTypeChange(event.target.value as ComponentType)
                }
                className="h-8 text-sm"
              >
                {componentTypeOptionsForCategory(productForm.equipment_category).map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-1">
              <Label htmlFor="product_equipment_category" className="text-[11px] text-muted-foreground">
                Category
              </Label>
              <Select
                id="product_equipment_category"
                value={productForm.equipment_category ?? ""}
                onChange={(event) =>
                  onProductFieldChange("equipment_category", event.target.value || undefined)
                }
                className="h-8 text-sm"
              >
                <option value="">Any</option>
                {EQUIPMENT_CATEGORY_OPTIONS.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-1">
              <Label htmlFor="product_refrigerant_type" className="text-[11px] text-muted-foreground">
                Refrigerant
              </Label>
              <Select
                id="product_refrigerant_type"
                value={productForm.refrigerant_type ?? ""}
                onChange={(event) =>
                  onProductFieldChange("refrigerant_type", event.target.value || undefined)
                }
                className="h-8 text-sm"
              >
                <option value="">Any</option>
                {REFRIGERANT_OPTIONS.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-1">
              <Label htmlFor="product_flow" className="text-[11px] text-muted-foreground">
                Flow
              </Label>
              <Select
                id="product_flow"
                value={productForm.flow ?? ""}
                onChange={(event) =>
                  onProductFieldChange("flow", event.target.value || undefined)
                }
                className="h-8 text-sm"
              >
                <option value="">Any</option>
                {FLOW_OPTIONS.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </Select>
            </div>

            {showCoilWidth && (
              <div className="space-y-1">
                <Label htmlFor="product_coil_width" className="text-[11px] text-muted-foreground">
                  Coil width
                </Label>
                <Select
                  id="product_coil_width"
                  value={productForm.coil_width ?? ""}
                  onChange={(event) =>
                    onProductFieldChange("coil_width", event.target.value || undefined)
                  }
                  className="h-8 text-sm"
                >
                  <option value="">Any</option>
                  {COIL_WIDTH_OPTIONS.map((value) => (
                    <option key={value} value={value}>
                      {formatWidthInches(value)}
                    </option>
                  ))}
                </Select>
              </div>
            )}

            {showFurnaceWidth && (
              <div className="space-y-1">
                <Label htmlFor="product_furnace_width" className="text-[11px] text-muted-foreground">
                  Furnace width
                </Label>
                <Select
                  id="product_furnace_width"
                  value={productForm.furnace_width ?? ""}
                  onChange={(event) =>
                    onProductFieldChange("furnace_width", event.target.value || undefined)
                  }
                  className="h-8 text-sm"
                >
                  <option value="">Any</option>
                  {FURNACE_WIDTH_OPTIONS.map((value) => (
                    <option key={value} value={value}>
                      {formatWidthInches(value)}
                    </option>
                  ))}
                </Select>
              </div>
            )}

            <div className="flex items-center justify-between rounded-md border px-2.5 py-1.5">
              <Label htmlFor="product_prefer_seer" className="text-xs">
                Prefer higher SEER
              </Label>
              <Switch
                id="product_prefer_seer"
                checked={productForm.prefer_higher_seer}
                onCheckedChange={(checked) => onProductFieldChange("prefer_higher_seer", checked)}
              />
            </div>

            <Button
              type="submit"
              size="sm"
              className="h-8 w-full"
              disabled={!productForm.model.trim() || isProductLoading}
            >
              {isProductLoading ? (
                <>
                  <Loader2 className="animate-spin" />
                  Searching…
                </>
              ) : (
                <>
                  <Search />
                  Find matchups
                </>
              )}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  )
}
