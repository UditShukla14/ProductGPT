import type { HvacRecommendation } from "@/types/api"
import { ChevronRight } from "lucide-react"

import { MatchupComponentImages } from "@/components/MatchupComponentImages"
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
  const title = system.description ?? "HVAC system"

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
        "flex min-h-[7.5rem] w-full min-w-0 cursor-pointer overflow-hidden rounded-xl border bg-card text-card-foreground transition-colors",
        "hover:border-primary/40 hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
      )}
    >
      <MatchupComponentImages
        components={system.components}
        fallbackImage={system.image_url}
        fallbackAlt={title}
      />

      <div className="flex min-w-0 flex-1 items-start justify-between gap-2 px-3 py-3">
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
          <h3 className="line-clamp-2 text-sm leading-snug font-semibold">{title}</h3>
          <p className="line-clamp-2 text-xs text-muted-foreground">{reason}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1 pt-0.5">
          <ScoreBadge score={score} />
          <ChevronRight className="size-3.5 text-muted-foreground" />
        </div>
      </div>
    </article>
  )
}
