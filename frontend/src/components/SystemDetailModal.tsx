import type { HvacRecommendation, HvacSystem } from "@/types/api"
import { Box, Flame, Package, Snowflake } from "lucide-react"

import { ProductImage } from "@/components/ProductImage"
import { ScoreBadge } from "@/components/ScoreBadge"

import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"

const componentIcon: Record<string, React.ReactNode> = {
  outdoor: <Snowflake className="size-4" />,
  coil: <Box className="size-4" />,
  furnace: <Flame className="size-4" />,
}

interface SystemDetailModalProps {
  recommendation: HvacRecommendation | null
  rank: number
  open: boolean
  onClose: () => void
}

function DetailItem({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value == null || value === "") return null
  return (
    <div className="rounded-lg border bg-muted/20 px-3 py-2.5">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-medium wrap-break-word">{value}</p>
    </div>
  )
}

function buildSpecificationFields(system: HvacSystem): Array<[string, string]> {
  if (system.all_fields && Object.keys(system.all_fields).length > 0) {
    return Object.entries(system.all_fields).sort(([a], [b]) => a.localeCompare(b))
  }

  const fallback: Array<[string, string | number | null | undefined]> = [
    ["SEER2", system.seer],
    ["EER", system.eer],
    ["HSPF", system.hspf],
    ["Cond SEER2", system.cond_seer],
    ["Tonnage", system.tonnage],
    ["Version", system.version],
    ["Equipment Category", system.equipment_category],
    ["Refrigerant", system.refrigerant_type],
    ["System Type", system.system_type],
    ["Cabinet Width", system.cabinet_width ? `${system.cabinet_width}"` : null],
    ["Blower Type", system.blower_type],
    ["Model Status", system.model_status],
    ["Outdoor Model", system.outdoor_model],
    ["Coil Model", system.coil_model],
    ["Furnace Model", system.furnace_model],
    ["AHRI Number", system.ahri_number],
    ["Row ID", system.source_row_id],
  ]

  return fallback
    .filter((entry): entry is [string, string | number] => entry[1] != null && entry[1] !== "")
    .map(([label, value]) => [label, String(value)])
}

export function SystemDetailModal({ recommendation, rank, open, onClose }: SystemDetailModalProps) {
  if (!recommendation) return null

  const { system, score, reason } = recommendation
  const specificationFields = buildSpecificationFields(system)

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogHeader
        title={system.description ?? "HVAC system details"}
        description={system.equipment_category ?? system.system_type ?? undefined}
        onClose={onClose}
      />

      <DialogContent className="space-y-6">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">Rank #{rank}</Badge>
          <ScoreBadge score={score} />
          {system.seer != null && <Badge variant="outline">SEER2 {system.seer}</Badge>}
          {system.tonnage != null && <Badge variant="outline">{system.tonnage} Ton</Badge>}
          {system.stage && <Badge variant="outline">{system.stage}</Badge>}
          {system.model_status && <Badge variant="success">{system.model_status}</Badge>}
        </div>

        {system.components.length > 0 && (
          <section>
            <h3 className="mb-3 text-sm font-semibold">Certified components</h3>
            <div className="grid gap-3 sm:grid-cols-3">
              {system.components.map((component) => (
                <div
                  key={`${component.type}-${component.model}`}
                  className="overflow-hidden rounded-lg border bg-background"
                >
                  <div className="border-b bg-muted/20 p-3">
                    <ProductImage
                      src={component.image_url}
                      alt={component.model}
                      className="min-h-24"
                      imageClassName="mx-auto max-h-28 object-contain"
                    />
                  </div>
                  <div className="px-4 py-3">
                    <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {componentIcon[component.type]}
                      {component.type}
                    </div>
                    <p className="font-mono text-sm font-semibold">{component.model}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {system.accessories && system.accessories.length > 0 && (
          <>
            <Separator />
            <section>
              <h3 className="mb-3 text-sm font-semibold">Accessories</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                {system.accessories.map((accessory) => (
                  <div
                    key={`${accessory.sku}-${accessory.source_model ?? "system"}`}
                    className="rounded-lg border bg-background px-4 py-3"
                  >
                    <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      <Package className="size-4" />
                      Accessory
                    </div>
                    <p className="font-mono text-sm font-semibold">{accessory.sku}</p>
                    {accessory.description && (
                      <p className="mt-1 text-sm text-muted-foreground">{accessory.description}</p>
                    )}
                    {accessory.source_model && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        From component: <span className="font-mono">{accessory.source_model}</span>
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          </>
        )}

        {specificationFields.length > 0 && (
          <>
            <Separator />
            <section>
              <h3 className="mb-3 text-sm font-semibold">Specifications</h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {specificationFields.map(([label, value]) => (
                  <DetailItem key={label} label={label} value={value} />
                ))}
              </div>
            </section>
          </>
        )}

        <section className="rounded-lg bg-muted/50 px-4 py-3">
          <h3 className="mb-1 text-sm font-semibold">Why recommended</h3>
          <p className="text-sm text-muted-foreground">{reason}</p>
        </section>
      </DialogContent>
    </Dialog>
  )
}
