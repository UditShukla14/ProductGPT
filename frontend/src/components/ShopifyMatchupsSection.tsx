import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Loader2, Sparkles } from "lucide-react"

import { CardCarousel } from "@/components/CardCarousel"
import { ShopifyMatchupCard } from "@/components/ShopifyMatchupCard"
import { SystemDetailModal } from "@/components/SystemDetailModal"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { componentTypeLabel } from "@/constants/hvac"
import { fetchShopifyMatchups } from "@/lib/api"
import type { HvacRecommendation } from "@/types/api"

const MATCHUP_LIMIT = 8

function RecommendationsSkeleton() {
  return (
    <div className="flex gap-3 overflow-hidden">
      {Array.from({ length: 4 }).map((_, index) => (
        <Skeleton key={index} className="h-72 w-48 shrink-0 rounded-xl" />
      ))}
    </div>
  )
}

interface ShopifyMatchupsSectionProps {
  productId: string
}

export function ShopifyMatchupsSection({ productId }: ShopifyMatchupsSectionProps) {
  const [selected, setSelected] = useState<{
    recommendation: HvacRecommendation
    rank: number
  } | null>(null)

  const matchupsQuery = useQuery({
    queryKey: ["shopify-matchups", productId],
    queryFn: () => fetchShopifyMatchups(productId, { limit: MATCHUP_LIMIT }),
    enabled: Boolean(productId),
  })

  const matchups = matchupsQuery.data?.similar_matchups ?? []
  const matchedType = matchupsQuery.data?.matched_type ?? null
  const matchedModel = matchupsQuery.data?.matched_model ?? matchupsQuery.data?.query ?? null
  const detailLabel =
    matchedModel != null
      ? `${componentTypeLabel(matchedType)} · ${matchedModel}`
      : null

  return (
    <>
      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Sparkles className="size-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            AHRI certified matchups
          </h3>
          {detailLabel && (
            <span className="text-xs text-muted-foreground">({detailLabel})</span>
          )}
          {matchupsQuery.isFetching && (
            <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
          )}
        </div>

        {matchupsQuery.isLoading ? (
          <RecommendationsSkeleton />
        ) : matchups.length === 0 ? (
          <Card className="shadow-none">
            <CardHeader className="py-4">
              <CardTitle className="text-sm font-normal text-muted-foreground">
                No AHRI-certified matchups found for this product&apos;s model in Goodman ratings.
              </CardTitle>
            </CardHeader>
          </Card>
        ) : (
          <CardCarousel
            slideClassName="w-48 shrink-0 basis-48 snap-start"
            ariaLabel="AHRI certified matchups"
          >
            {matchups.map((recommendation, index) => (
              <ShopifyMatchupCard
                key={`${recommendation.system.id}-${index}`}
                recommendation={recommendation}
                onClick={(item) => setSelected({ recommendation: item, rank: index + 1 })}
              />
            ))}
          </CardCarousel>
        )}
      </section>

      <SystemDetailModal
        open={selected != null}
        recommendation={selected?.recommendation ?? null}
        rank={selected?.rank ?? 0}
        onClose={() => setSelected(null)}
      />
    </>
  )
}
