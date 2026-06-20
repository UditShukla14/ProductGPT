import type { HvacRecommendation } from "@/types/api"
import { ChevronRight } from "lucide-react"

import { ScoreBadge } from "@/components/ScoreBadge"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface SystemCardProps {
  recommendation: HvacRecommendation
  rank: number
  onClick: () => void
}

export function SystemCard({ recommendation, rank, onClick }: SystemCardProps) {
  const { system, score, reason } = recommendation

  return (
    <article
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault()
          onClick()
        }
      }}
      className={cn(
        "flex cursor-pointer flex-col rounded-xl border bg-card text-card-foreground transition-colors",
        "hover:border-primary/40 hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
      )}
    >
      <div className="flex items-start justify-between gap-2 px-4 py-3">
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-1">
            <Badge variant="secondary" className="px-1.5 py-0 text-[10px]">
              #{rank}
            </Badge>
            {system.seer != null && (
              <Badge variant="outline" className="px-1.5 py-0 text-[10px]">
                SEER {system.seer}
              </Badge>
            )}
            {system.tonnage != null && (
              <Badge variant="outline" className="px-1.5 py-0 text-[10px]">
                {system.tonnage}T
              </Badge>
            )}
            {system.refrigerant_type && (
              <Badge variant="outline" className="px-1.5 py-0 text-[10px]">
                {system.refrigerant_type}
              </Badge>
            )}
            {system.equipment_category && (
              <Badge variant="outline" className="px-1.5 py-0 text-[10px]">
                {system.equipment_category}
              </Badge>
            )}
          </div>
          <h3 className="text-sm leading-snug font-semibold">
            {system.description ?? "HVAC system"}
          </h3>
          <p className="text-xs text-muted-foreground">{reason}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <ScoreBadge score={score} />
          <ChevronRight className="size-3.5 text-muted-foreground" />
        </div>
      </div>
    </article>
  )
}
