import type { BoughtTogetherItem } from "@/types/api"
import { Box, Flame, Package, Snowflake } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const typeConfig = {
  outdoor: {
    label: "Outdoor units",
    icon: Snowflake,
    description: "Compatible condensers certified with your search",
  },
  coil: {
    label: "Evaporator coils",
    icon: Box,
    description: "Compatible coils to complete the matchup",
  },
  furnace: {
    label: "Furnaces",
    icon: Flame,
    description: "Compatible furnaces to complete the matchup",
  },
} as const

interface BoughtTogetherSectionProps {
  items: BoughtTogetherItem[]
  searchedType: "outdoor" | "coil" | "furnace" | null
}

export function BoughtTogetherSection({ items, searchedType }: BoughtTogetherSectionProps) {
  if (items.length === 0) return null

  const grouped = (["outdoor", "coil", "furnace"] as const)
    .filter((type) => type !== searchedType)
    .map((type) => ({
      type,
      items: items.filter((item) => item.type === type),
    }))
    .filter((group) => group.items.length > 0)

  return (
    <section className="space-y-4">
      <div>
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Package className="size-5" />
          Frequently bought together
        </h2>
        <p className="text-sm text-muted-foreground">
          Other certified components paired with your model in AHRI matchups
        </p>
      </div>

      <div className="space-y-4">
        {grouped.map(({ type, items: groupItems }) => {
          const config = typeConfig[type]
          const Icon = config.icon

          return (
            <Card key={type}>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Icon className="size-4" />
                  {config.label}
                </CardTitle>
                <CardDescription>{config.description}</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-2 sm:grid-cols-2">
                {groupItems.map((item) => (
                  <div
                    key={`${item.type}-${item.model}`}
                    className="flex items-start justify-between gap-3 rounded-lg border bg-muted/20 px-3 py-2.5"
                  >
                    <div className="min-w-0">
                      <p className="font-mono text-sm font-semibold">{item.model}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {item.matchup_count} certified matchup{item.matchup_count === 1 ? "" : "s"}
                      </p>
                    </div>
                    {item.best_seer != null && (
                      <Badge variant="outline" className="shrink-0">
                        SEER {item.best_seer}
                      </Badge>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </section>
  )
}
