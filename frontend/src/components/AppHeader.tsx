import { useQuery } from "@tanstack/react-query"
import { Activity, Database, Loader2, Search } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import {
  COMPONENT_TYPE_OPTIONS,
  EQUIPMENT_CATEGORY_OPTIONS,
  REFRIGERANT_OPTIONS,
  componentTypePlaceholder,
} from "@/constants/hvac"
import { fetchHealth } from "@/lib/api"
import type { ComponentType } from "@/types/api"

interface AppHeaderProps {
  productModel: string
  componentType: ComponentType
  equipmentCategory?: string
  refrigerantType?: string
  preferHigherSeer: boolean
  isProductSearching: boolean
  onProductModelChange: (value: string) => void
  onComponentTypeChange: (value: ComponentType) => void
  onEquipmentCategoryChange: (value: string | undefined) => void
  onRefrigerantTypeChange: (value: string | undefined) => void
  onPreferHigherSeerChange: (value: boolean) => void
  onProductSubmit: (event: React.FormEvent) => void
}

export function AppHeader({
  productModel,
  componentType,
  equipmentCategory,
  refrigerantType,
  preferHigherSeer,
  isProductSearching,
  onProductModelChange,
  onComponentTypeChange,
  onEquipmentCategoryChange,
  onRefrigerantTypeChange,
  onPreferHigherSeerChange,
  onProductSubmit,
}: AppHeaderProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  })

  return (
    <header
      id="app-header"
      className="sticky top-0 z-40 w-full max-w-[100vw] overflow-x-clip border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/90"
    >
      <div className="mx-auto w-full max-w-7xl min-w-0 px-4 py-3 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-base font-semibold tracking-tight sm:text-lg">
              ProductGPT · HVAC System Finder
            </h1>
            <p className="text-xs text-muted-foreground">
              Goodman AHRI-certified matchups
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {isLoading ? (
              <Badge variant="secondary" className="text-xs">
                Checking…
              </Badge>
            ) : isError ? (
              <Badge variant="outline" className="text-xs">
                Offline
              </Badge>
            ) : (
              <>
                <Badge variant="success" className="gap-1 text-xs">
                  <Activity className="size-3" />
                  {data?.status ?? "unknown"}
                </Badge>
                <Badge variant="secondary" className="gap-1 text-xs">
                  <Database className="size-3" />
                  {(data?.hvac_system_count ?? 0).toLocaleString()} systems
                </Badge>
                {data?.neo4j_connected && (
                  <Badge variant="outline" className="text-xs">
                    Neo4j
                  </Badge>
                )}
              </>
            )}
          </div>
        </div>

        <form
          onSubmit={onProductSubmit}
          className="mt-3 rounded-lg border bg-muted/40 p-2.5"
        >
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-[minmax(0,1.5fr)_repeat(4,minmax(0,1fr))_auto_auto] lg:items-end">
            <div className="space-y-1">
              <Label htmlFor="product_model" className="text-[11px] text-muted-foreground">
                Model number
              </Label>
              <Input
                id="product_model"
                placeholder={componentTypePlaceholder(componentType)}
                value={productModel}
                onChange={(event) => onProductModelChange(event.target.value)}
                className="h-8 bg-background text-sm"
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="component_type" className="text-[11px] text-muted-foreground">
                Component
              </Label>
              <Select
                id="component_type"
                value={componentType}
                onChange={(event) => onComponentTypeChange(event.target.value as ComponentType)}
                className="h-8 bg-background text-sm"
              >
                {COMPONENT_TYPE_OPTIONS.map((option) => (
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
                value={equipmentCategory ?? ""}
                onChange={(event) => onEquipmentCategoryChange(event.target.value || undefined)}
                className="h-8 bg-background text-sm"
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
                value={refrigerantType ?? ""}
                onChange={(event) => onRefrigerantTypeChange(event.target.value || undefined)}
                className="h-8 bg-background text-sm"
              >
                <option value="">Any</option>
                {REFRIGERANT_OPTIONS.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </Select>
            </div>

            <div className="flex h-8 items-center justify-between gap-2 rounded-md border bg-background px-2.5">
              <Label htmlFor="prefer_higher_seer" className="text-xs font-medium">
                Higher SEER
              </Label>
              <Switch
                id="prefer_higher_seer"
                checked={preferHigherSeer}
                onCheckedChange={onPreferHigherSeerChange}
              />
            </div>

            <Button
              type="submit"
              size="sm"
              disabled={!productModel.trim() || isProductSearching}
              className="h-8 w-full lg:w-auto"
            >
              {isProductSearching ? (
                <>
                  <Loader2 className="animate-spin" />
                  Searching…
                </>
              ) : (
                <>
                  <Search />
                  Find
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </header>
  )
}
