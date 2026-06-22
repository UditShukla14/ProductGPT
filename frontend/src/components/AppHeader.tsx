import { useQuery } from "@tanstack/react-query"
import { Activity, Database } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { fetchHealth } from "@/lib/api"

export function AppHeader() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  })

  return (
    <header
      id="app-header"
      className="sticky top-0 z-40 w-full max-w-[100vw] overflow-x-clip border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/90"
    >
      <div className="mx-auto flex w-full max-w-7xl min-w-0 flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="min-w-0">
          <h1 className="text-base font-semibold tracking-tight sm:text-lg">
            ProductGPT · HVAC System Finder
          </h1>
          <p className="text-xs text-muted-foreground">Goodman AHRI-certified matchups</p>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {isLoading ? (
            <Badge variant="secondary" className="text-xs">
              Checking…
            </Badge>
          ) : isError ? (
            <Badge variant="outline" className="text-xs">
              Offline
            </Badge>
          ) : (
            <>
              <Badge variant="success" className="gap-1 text-xs">
                <Activity className="size-3" />
                {data?.status ?? "unknown"}
              </Badge>
              <Badge variant="secondary" className="gap-1 text-xs">
                <Database className="size-3" />
                {(data?.hvac_system_count ?? 0).toLocaleString()} systems
              </Badge>
              {data?.neo4j_connected && (
                <Badge variant="outline" className="text-xs">
                  Neo4j
                </Badge>
              )}
            </>
          )}
        </div>
      </div>
    </header>
  )
}
