import { useInfiniteQuery } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"

import { SystemCard } from "@/components/SystemCard"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { COMPONENT_TYPE_LABELS } from "@/constants/hvac"
import { fetchPairedMatchups } from "@/lib/api"
import type { BoughtTogetherItem, HvacRecommendation } from "@/types/api"

const PAGE_SIZE = 25

interface BoughtTogetherMatchupsModalProps {
  open: boolean
  onClose: () => void
  anchorType: "outdoor" | "coil" | "furnace"
  anchorModel: string
  item: BoughtTogetherItem | null
  equipmentCategory?: string
  refrigerantType?: string
  flow?: string
  coilWidth?: string
  furnaceWidth?: string
  preferHigherSeer?: boolean
  onSelectMatchup: (recommendation: HvacRecommendation, rank: number) => void
}

export function BoughtTogetherMatchupsModal({
  open,
  onClose,
  anchorType,
  anchorModel,
  item,
  equipmentCategory,
  refrigerantType,
  flow,
  coilWidth,
  furnaceWidth,
  preferHigherSeer = true,
  onSelectMatchup,
}: BoughtTogetherMatchupsModalProps) {
  const query = useInfiniteQuery({
    queryKey: [
      "paired-matchups",
      anchorType,
      anchorModel,
      item?.type,
      item?.model,
      equipmentCategory,
      refrigerantType,
      flow,
      coilWidth,
      furnaceWidth,
      preferHigherSeer,
    ],
    queryFn: ({ pageParam }) =>
      fetchPairedMatchups({
        anchor_type: anchorType,
        anchor_model: anchorModel,
        paired_type: item!.type,
        paired_model: item!.model,
        equipment_category: equipmentCategory,
        refrigerant_type: refrigerantType,
        flow,
        coil_width: item?.type === "coil" ? coilWidth : undefined,
        furnace_width: item?.type === "furnace" ? furnaceWidth : undefined,
        limit: PAGE_SIZE,
        offset: pageParam,
        prefer_higher_seer: preferHigherSeer,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) =>
      lastPage.meta.has_more ? lastPage.meta.offset + lastPage.meta.returned : undefined,
    enabled: open && item != null,
  })

  const matchups = query.data?.pages.flatMap((page) => page.matchups) ?? []
  const total = query.data?.pages[query.data.pages.length - 1]?.meta.total_matchups ?? 0
  const isInitialLoading = query.isFetching && matchups.length === 0

  if (!item) return null

  return (
    <Dialog open={open} onClose={onClose} className="max-w-4xl">
      <DialogHeader
        title={`${COMPONENT_TYPE_LABELS[item.type]} matchups`}
        description={`${item.matchup_count} certified AHRI system${item.matchup_count === 1 ? "" : "s"} pairing ${COMPONENT_TYPE_LABELS[item.type].toLowerCase()} ${item.model} with your ${COMPONENT_TYPE_LABELS[anchorType].toLowerCase()} ${anchorModel}`}
        onClose={onClose}
      />

      <DialogContent className="space-y-4">
        {query.isError && (
          <Alert variant="destructive">
            <AlertTitle>Could not load matchups</AlertTitle>
            <AlertDescription>
              {query.error instanceof Error ? query.error.message : "Unknown error"}
            </AlertDescription>
          </Alert>
        )}

        {isInitialLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((key) => (
              <Skeleton key={key} className="h-[7.5rem] w-full rounded-xl" />
            ))}
          </div>
        )}

        {!isInitialLoading && matchups.length === 0 && !query.isError && (
          <Alert>
            <AlertTitle>No matchups found</AlertTitle>
            <AlertDescription>
              No certified systems were found for this component pairing.
            </AlertDescription>
          </Alert>
        )}

        {matchups.length > 0 && (
          <div className="max-h-[min(60vh,32rem)] space-y-2 overflow-y-auto pr-1">
            {matchups.map((recommendation, index) => (
              <SystemCard
                key={recommendation.system.id}
                recommendation={recommendation}
                rank={index + 1}
                onClick={() => onSelectMatchup(recommendation, index + 1)}
              />
            ))}
          </div>
        )}

        {matchups.length > 0 && (
          <div className="flex items-center justify-between gap-4 border-t pt-4">
            <p className="text-sm text-muted-foreground">
              Showing {matchups.length} of {total}
            </p>
            {query.hasNextPage ? (
              <Button
                type="button"
                variant="outline"
                disabled={query.isFetchingNextPage}
                onClick={() => query.fetchNextPage()}
              >
                {query.isFetchingNextPage ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Loading…
                  </>
                ) : (
                  `Load ${PAGE_SIZE} more`
                )}
              </Button>
            ) : (
              <p className="text-sm text-muted-foreground">All matchups loaded</p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
