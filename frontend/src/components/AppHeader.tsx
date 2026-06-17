import { useQuery } from "@tanstack/react-query"
import { Activity, Database, Loader2, Search } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { fetchHealth } from "@/lib/api"
import type { ComponentType } from "@/types/api"

interface AppHeaderProps {
  productModel: string
  componentType: ComponentType
  preferHigherSeer: boolean
  isProductSearching: boolean
  onProductModelChange: (value: string) => void
  onComponentTypeChange: (value: ComponentType) => void
  onPreferHigherSeerChange: (value: boolean) => void
  onProductSubmit: (event: React.FormEvent) => void
}

export function AppHeader({
  productModel,
  componentType,
  preferHigherSeer,
  isProductSearching,
  onProductModelChange,
  onComponentTypeChange,
  onPreferHigherSeerChange,
  onProductSubmit,
}: AppHeaderProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  })

  return (
    <header id="app-header" className="sticky top-0 z-40 border-b bg-card/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="mx-auto max-w-7xl space-y-4 px-4 py-4 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
              ProductGPT
            </p>
            <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">HVAC System Finder</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              AHRI-certified recommendations from your knowledge base
            </p>
          </div>

          <div className="flex items-center gap-2">
            {isLoading ? (
              <Badge variant="secondary">Checking status…</Badge>
            ) : isError ? (
              <Badge variant="outline">API offline</Badge>
            ) : (
              <>
                <Badge variant="success" className="gap-1">
                  <Activity className="size-3" />
                  {data?.status ?? "unknown"}
                </Badge>
                <Badge variant="secondary" className="gap-1">
                  <Database className="size-3" />
                  {data?.hvac_system_count ?? 0} systems
                </Badge>
              </>
            )}
          </div>
        </div>

        <form
          onSubmit={onProductSubmit}
          className="flex flex-col gap-3 rounded-xl border bg-muted/30 p-3 lg:flex-row lg:items-end"
        >
          <div className="min-w-0 flex-1 space-y-1.5">
            <Label htmlFor="product_model" className="text-xs text-muted-foreground">
              Search by product
            </Label>
            <Input
              id="product_model"
              placeholder="Outdoor, coil, or furnace model — e.g. GSXN402410"
              value={productModel}
              onChange={(event) => onProductModelChange(event.target.value)}
              className="bg-background"
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:flex lg:items-end">
            <div className="space-y-1.5 sm:min-w-40">
              <Label htmlFor="component_type" className="text-xs text-muted-foreground">
                Component type
              </Label>
              <Select
                id="component_type"
                value={componentType}
                onChange={(event) => onComponentTypeChange(event.target.value as ComponentType)}
                className="bg-background"
              >
                <option value="auto">Auto-detect</option>
                <option value="outdoor">Outdoor unit</option>
                <option value="coil">Coil</option>
                <option value="furnace">Furnace</option>
              </Select>
            </div>

            <div className="flex h-8 items-center justify-between gap-3 rounded-lg border bg-background px-3 sm:min-w-44">
              <Label htmlFor="prefer_higher_seer" className="text-sm font-medium">
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
              disabled={!productModel.trim() || isProductSearching}
              className="w-full sm:w-auto"
            >
              {isProductSearching ? (
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
          </div>
        </form>
      </div>
    </header>
  )
}
