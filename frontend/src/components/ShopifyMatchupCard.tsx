import type { HvacRecommendation } from "@/types/api"

import { MatchupComponentImages } from "@/components/MatchupComponentImages"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface ShopifyMatchupCardProps {
  recommendation: HvacRecommendation
  onClick?: (recommendation: HvacRecommendation) => void
  className?: string
}

function CardBody({ recommendation }: { recommendation: HvacRecommendation }) {
  const { system, reason } = recommendation
  const title = system.description ?? "AHRI certified system"

  return (
    <>
      <div className="aspect-square w-full shrink-0 overflow-hidden rounded-md border bg-muted/30">
        <MatchupComponentImages
          components={system.components}
          fallbackImage={system.image_url}
          fallbackAlt={title}
          compact
          spread
          className="size-full w-full border-0"
        />
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-1.5 p-3 pt-2">
        <p className="line-clamp-2 min-h-10 text-sm font-medium leading-5">{title}</p>

        <div className="flex min-h-5 flex-wrap items-center gap-1">
          {system.seer != null && (
            <Badge variant="secondary" className="shrink-0 text-[10px]">
              SEER2 {system.seer}
            </Badge>
          )}
          {system.tonnage != null && (
            <Badge variant="outline" className="shrink-0 text-[10px]">
              {system.tonnage}T
            </Badge>
          )}
          {system.ahri_number && (
            <Badge variant="outline" className="max-w-full truncate font-mono text-[10px]">
              {system.ahri_number}
            </Badge>
          )}
        </div>

        {reason && (
          <p className="mt-auto line-clamp-2 text-[11px] text-muted-foreground">{reason}</p>
        )}
      </div>
    </>
  )
}

export function ShopifyMatchupCard({ recommendation, onClick, className }: ShopifyMatchupCardProps) {
  if (!onClick) {
    return (
      <div className={cn("flex h-full flex-col overflow-hidden rounded-xl border bg-card", className)}>
        <CardBody recommendation={recommendation} />
      </div>
    )
  }

  return (
    <button
      type="button"
      onClick={() => onClick(recommendation)}
      className={cn(
        "flex h-full w-full flex-col overflow-hidden rounded-xl border bg-card text-left transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        className
      )}
    >
      <CardBody recommendation={recommendation} />
    </button>
  )
}
