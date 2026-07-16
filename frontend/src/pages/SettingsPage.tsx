import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  CheckCircle2,
  Loader2,
  Package,
  RefreshCw,
  ShoppingCart,
  Users,
  XCircle,
} from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { fetchShopifySyncStatus, startShopifySync } from "@/lib/api"
import type { ShopifySyncStartRequest } from "@/types/api"

type SyncResource = "products" | "customers" | "orders"

const RESOURCES: Array<{
  key: SyncResource
  title: string
  description: string
  icon: typeof Package
  countKey: "products" | "customers" | "orders"
}> = [
  {
    key: "products",
    title: "Products",
    description: "Sync Shopify product catalog into the local products database.",
    icon: Package,
    countKey: "products",
  },
  {
    key: "customers",
    title: "Customers",
    description: "Sync Shopify customers into the local customers database.",
    icon: Users,
    countKey: "customers",
  },
  {
    key: "orders",
    title: "Orders",
    description: "Sync Shopify orders for bought-together recommendations.",
    icon: ShoppingCart,
    countKey: "orders",
  },
]

function formatTime(value: string | null | undefined) {
  if (!value) return "—"
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

export function SettingsPage() {
  const queryClient = useQueryClient()

  const { data: syncStatus, isLoading, isError, error } = useQuery({
    queryKey: ["shopify-sync-status"],
    queryFn: fetchShopifySyncStatus,
    refetchInterval: (query) =>
      query.state.data?.job.state === "running" ? 2_000 : 15_000,
    staleTime: 2_000,
  })

  const mutation = useMutation({
    mutationFn: (payload: ShopifySyncStartRequest) => startShopifySync(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["shopify-sync-status"] })
    },
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: ["shopify-sync-status"] })
    },
  })

  const job = syncStatus?.job
  const isRunning = job?.state === "running" || mutation.isPending
  const mutationError = mutation.error instanceof Error ? mutation.error.message : null

  function startResource(resource: SyncResource) {
    mutation.mutate({ resources: [resource], rebuild_graph: true })
  }

  function startAll() {
    mutation.mutate({
      resources: ["products", "customers", "orders"],
      rebuild_graph: true,
    })
  }

  return (
    <main className="mx-auto w-full max-w-5xl min-w-0 space-y-6 px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Settings</h2>
          <p className="text-sm text-muted-foreground">
            Sync Shopify resources separately and track live progress.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={isRunning}
          onClick={startAll}
          className="gap-1.5"
        >
          {isRunning ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
          Sync all
        </Button>
      </div>

      {(isError || mutationError) && (
        <Alert variant="destructive">
          <AlertTitle>Sync error</AlertTitle>
          <AlertDescription>
            {mutationError ??
              (error instanceof Error ? error.message : "Could not load sync status.")}
          </AlertDescription>
        </Alert>
      )}

      <section className="grid gap-4 sm:grid-cols-3">
        {RESOURCES.map((resource) => {
          const Icon = resource.icon
          const count = syncStatus?.[resource.countKey] ?? 0
          const result = job?.results?.find((item) => item.resource === resource.key)
          const isActive =
            isRunning &&
            (job?.current_resource === resource.key ||
              (mutation.isPending &&
                mutation.variables?.resources?.length === 1 &&
                mutation.variables.resources[0] === resource.key))

          return (
            <Card key={resource.key} className="shadow-none">
              <CardHeader className="space-y-3 pb-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Icon className="size-4 text-muted-foreground" />
                    <CardTitle className="text-base">{resource.title}</CardTitle>
                  </div>
                  <Badge variant="secondary" className="tabular-nums">
                    {isLoading ? "…" : count.toLocaleString()}
                  </Badge>
                </div>
                <CardDescription className="text-xs leading-relaxed">
                  {resource.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {result && (
                  <p className="text-[11px] text-muted-foreground">
                    Last run: {result.status}
                    {typeof result.fetched === "number"
                      ? ` · fetched ${result.fetched.toLocaleString()}`
                      : ""}
                    {typeof result.details_fetched === "number" && result.details_fetched > 0
                      ? ` · details ${result.details_fetched.toLocaleString()}`
                      : ""}
                  </p>
                )}
                <Button
                  type="button"
                  className="w-full gap-1.5"
                  disabled={isRunning}
                  onClick={() => startResource(resource.key)}
                >
                  {isActive ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="size-3.5" />
                  )}
                  {isActive ? `Syncing ${resource.title.toLowerCase()}…` : `Sync ${resource.title}`}
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </section>

      <Card className="shadow-none">
        <CardHeader>
          <CardTitle className="text-base">Sync progress</CardTitle>
          <CardDescription className="text-xs">
            Live status from the server job. Polls every few seconds while a sync is running.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant={
                job?.state === "failed"
                  ? "destructive"
                  : job?.state === "completed"
                    ? "success"
                    : job?.state === "running"
                      ? "secondary"
                      : "outline"
              }
              className="capitalize"
            >
              {job?.state ?? "idle"}
            </Badge>
            {job?.phase && (
              <Badge variant="outline" className="capitalize">
                {job.phase.replaceAll("_", " ")}
              </Badge>
            )}
            {job?.current_resource && (
              <Badge variant="outline" className="capitalize">
                Current: {job.current_resource}
              </Badge>
            )}
            {job?.graph_rebuilt && <Badge variant="outline">Graph rebuilt</Badge>}
          </div>

          <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
            <p>
              Started: <span className="text-foreground">{formatTime(job?.started_at)}</span>
            </p>
            <p>
              Finished: <span className="text-foreground">{formatTime(job?.finished_at)}</span>
            </p>
            <p className="sm:col-span-2">
              Requested:{" "}
              <span className="text-foreground">
                {(job?.requested_resources?.length
                  ? job.requested_resources
                  : ["products", "customers", "orders"]
                ).join(", ")}
              </span>
            </p>
          </div>

          {job?.error && (
            <Alert variant="destructive">
              <XCircle className="size-4" />
              <AlertTitle>Job failed</AlertTitle>
              <AlertDescription>{job.error}</AlertDescription>
            </Alert>
          )}

          {job?.state === "completed" && !job.error && (
            <Alert>
              <CheckCircle2 className="size-4" />
              <AlertTitle>Sync completed</AlertTitle>
              <AlertDescription>
                {job.graph_rebuilt
                  ? "Resources synced and Shopify graph rebuilt."
                  : "Resources synced."}
              </AlertDescription>
            </Alert>
          )}

          {job?.results && job.results.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[28rem] text-left text-xs">
                <thead className="border-b bg-muted/40 text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">Resource</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2 font-medium">Fetched</th>
                    <th className="px-3 py-2 font-medium">In DB</th>
                    <th className="px-3 py-2 font-medium">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {job.results.map((result) => (
                    <tr key={result.resource} className="border-b last:border-0">
                      <td className="px-3 py-2 capitalize">{result.resource}</td>
                      <td className="px-3 py-2 capitalize">{result.status}</td>
                      <td className="px-3 py-2 tabular-nums">
                        {result.fetched.toLocaleString()}
                      </td>
                      <td className="px-3 py-2 tabular-nums">
                        {result.total_in_db.toLocaleString()}
                      </td>
                      <td className="px-3 py-2 tabular-nums">
                        {(result.details_fetched ?? 0).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              No sync results yet. Start a product, customer, or order sync above.
            </p>
          )}
        </CardContent>
      </Card>
    </main>
  )
}
