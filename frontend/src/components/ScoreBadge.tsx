import { Star } from "lucide-react"

import { formatScore, getScoreBadgeClass } from "@/lib/score"
import { cn } from "@/lib/utils"

interface ScoreBadgeProps {
  score: number
  className?: string
}

export function ScoreBadge({ score, className }: ScoreBadgeProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-1 rounded-lg px-2.5 py-1 text-sm font-semibold",
        getScoreBadgeClass(score),
        className
      )}
    >
      <Star className="size-3.5 fill-current" />
      {formatScore(score)}
    </div>
  )
}
