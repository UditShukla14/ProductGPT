import type { HvacRecommendation } from "@/types/api"
import { ChevronRight } from "lucide-react"

import { ScoreBadge } from "@/components/ScoreBadge"
import { Badge } from "@/components/ui/badge"
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface SystemCardProps {
  recommendation: HvacRecommendation
  rank: number
  onClick: () => void
}

export function SystemCard({ recommendation, rank, onClick }: SystemCardProps) {
  const { system, score, reason } = recommendation

  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault()
          onClick()
        }
      }}
      className={cn(
        "cursor-pointer overflow-hidden transition-colors hover:border-primary/40 hover:bg-muted/20 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
      )}
    >
      <CardHeader className="gap-3 pb-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">#{rank}</Badge>
              {system.seer != null && <Badge variant="outline">SEER {system.seer}</Badge>}
              {system.tonnage != null && <Badge variant="outline">{system.tonnage} Ton</Badge>}
              {system.stage && <Badge variant="outline">{system.stage}</Badge>}
              {system.model_status && <Badge variant="success">{system.model_status}</Badge>}
            </div>
            <CardTitle className="text-base leading-snug">
              {system.description ?? "HVAC system"}
            </CardTitle>
            <CardDescription className="line-clamp-2">
              {system.system_type_seer2 ?? system.system_type}
            </CardDescription>
            <p className="line-clamp-2 text-sm text-muted-foreground">{reason}</p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            <ScoreBadge score={score} />
            <span className="flex items-center gap-1 text-xs font-medium text-primary">
              View details
              <ChevronRight className="size-3.5" />
            </span>
          </div>
        </div>
      </CardHeader>
    </Card>
  )
}
