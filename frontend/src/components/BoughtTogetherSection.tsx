import { Box, ChevronRight, Flame, Package, Snowflake } from "lucide-react"

import { CardCarousel } from "@/components/CardCarousel"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { COMPONENT_SECTION_CONFIG } from "@/constants/hvac"
import { cn } from "@/lib/utils"
import type { BoughtTogetherItem } from "@/types/api"

const typeIcons = {
  outdoor: Snowflake,
  coil: Box,
  furnace: Flame,
} as const

interface BoughtTogetherSectionProps {
  items: BoughtTogetherItem[]
  searchedType: "outdoor" | "coil" | "furnace" | null
  onItemClick?: (item: BoughtTogetherItem) => void
}

export function BoughtTogetherSection({
  items,
  searchedType,
  onItemClick,
}: BoughtTogetherSectionProps) {
  if (items.length === 0) return null

  const grouped = (["outdoor", "coil", "furnace"] as const)
    .filter((type) => type !== searchedType)
    .map((type) => ({
      type,
      items: items.filter((item) => item.type === type),
    }))
    .filter((group) => group.items.length > 0)

  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2">
        <Package className="size-3.5 text-muted-foreground" />
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Frequently bought together
        </h2>
      </div>

      <CardCarousel
        ariaLabel="Frequently bought together sections"
        slideClassName="w-[min(100%,20rem)] sm:w-[22rem]"
      >
        {grouped.map(({ type, items: groupItems }) => {
          const config = COMPONENT_SECTION_CONFIG[type]
          const Icon = typeIcons[type]
          const isClickable = (type === "coil" || type === "furnace") && onItemClick != null

          return (
            <Card key={type} className="gap-0 py-0 shadow-none">
              <CardHeader className="gap-1 px-3 py-2.5">
                <CardTitle className="flex items-center gap-1.5 text-sm">
                  <Icon className="size-3.5" />
                  {config.label}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1.5 px-3 pb-3">
                {groupItems.slice(0, 6).map((item) => {
                  const content = (
                    <>
                      <div className="min-w-0">
                        <p className="truncate font-mono text-xs font-medium">{item.model}</p>
                        <p className="text-[10px] text-muted-foreground">
                          {item.matchup_count} matchup{item.matchup_count === 1 ? "" : "s"}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
                        {item.best_seer != null && (
                          <Badge variant="outline" className="px-1 py-0 text-[10px]">
                            {item.best_seer}
                          </Badge>
                        )}
                        {isClickable && <ChevronRight className="size-3 text-primary" />}
                      </div>
                    </>
                  )

                  const className = cn(
                    "flex w-full items-center justify-between gap-2 rounded-md border px-2 py-1.5 text-left",
                    isClickable
                      ? "bg-muted/30 transition-colors hover:border-primary/40 hover:bg-primary/5"
                      : "bg-muted/20"
                  )

                  if (!isClickable) {
                    return (
                      <div key={`${item.type}-${item.model}`} className={className}>
                        {content}
                      </div>
                    )
                  }

                  return (
                    <button
                      key={`${item.type}-${item.model}`}
                      type="button"
                      onClick={() => onItemClick(item)}
                      className={cn(
                        className,
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                      )}
                    >
                      {content}
                    </button>
                  )
                })}
              </CardContent>
            </Card>
          )
        })}
      </CardCarousel>
    </section>
  )
}
