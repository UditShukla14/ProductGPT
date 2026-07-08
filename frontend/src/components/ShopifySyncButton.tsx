import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { fetchShopifySyncStatus, startShopifySync } from "@/lib/api"

function syncLabel(
  state: string | undefined,
  currentResource: string | null | undefined,
  phase: string | null | undefined
) {
  if (state === "running") {
    if (phase === "rebuilding_graph") return "Rebuilding graph…"
    if (currentResource) return `Syncing ${currentResource}…`
    return "Syncing…"
  }
  if (state === "completed") return "Sync complete"
  if (state === "failed") return "Sync failed"
  return "Sync now"
}

export function ShopifySyncButton() {
  const queryClient = useQueryClient()

  const { data: syncStatus } = useQuery({
    queryKey: ["shopify-sync-status"],
    queryFn: fetchShopifySyncStatus,
    refetchInterval: (query) =>
      query.state.data?.job.state === "running" ? 3_000 : 60_000,
    staleTime: 5_000,
  })

  const mutation = useMutation({
    mutationFn: startShopifySync,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["shopify-sync-status"] })
    },
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: ["shopify-sync-status"] })
    },
  })

  const job = syncStatus?.job
  const isRunning = job?.state === "running" || mutation.isPending
  const label = syncLabel(job?.state, job?.current_resource, job?.phase)

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="h-7 gap-1.5 text-xs"
      disabled={isRunning}
      title={job?.error ?? undefined}
      onClick={() => mutation.mutate()}
    >
      {isRunning ? (
        <Loader2 className="size-3 animate-spin" />
      ) : (
        <RefreshCw className="size-3" />
      )}
      {mutation.isPending && !job ? "Starting…" : label}
    </Button>
  )
}
