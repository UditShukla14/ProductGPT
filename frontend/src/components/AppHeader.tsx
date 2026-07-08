import { useQuery } from "@tanstack/react-query"
import { Activity, Database, Package, ShoppingCart, Users } from "lucide-react"
import { Link, useLocation } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { fetchHealth, fetchShopifySyncStatus } from "@/lib/api"

const NAV_ITEMS = [
  { to: "/", label: "HVAC" },
  { to: "/shopify", label: "Shopify" },
] as const

export function AppHeader() {
  const location = useLocation()
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  })

  const { data: shopifyStatus, isLoading: isShopifyStatusLoading } = useQuery({
    queryKey: ["shopify-sync-status"],
    queryFn: fetchShopifySyncStatus,
    refetchInterval: 60_000,
    staleTime: 30_000,
  })

  const isShopify = location.pathname.startsWith("/shopify")

  return (
    <header
      id="app-header"
      className="sticky top-0 z-40 w-full max-w-[100vw] overflow-x-clip border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/90"
    >
      <div className="mx-auto flex w-full max-w-7xl min-w-0 flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex min-w-0 flex-wrap items-center gap-4">
          <div className="min-w-0">
            <h1 className="text-base font-semibold tracking-tight sm:text-lg">
              ProductGPT
              {isShopify ? " · Shopify Catalog" : " · HVAC System Finder"}
            </h1>
            <p className="text-xs text-muted-foreground">
              {isShopify
                ? "Search synced products and order-based recommendations"
                : "Goodman AHRI-certified matchups"}
            </p>
          </div>

          <nav className="flex items-center gap-1 rounded-lg border bg-muted/40 p-0.5">
            {NAV_ITEMS.map((item) => {
              const active =
                item.to === "/"
                  ? location.pathname === "/"
                  : location.pathname.startsWith(item.to)
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={cn(
                    "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                    active
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {item.label}
                </Link>
              )
            })}
          </nav>

          <div className="flex flex-wrap items-center gap-1.5">
            {isShopifyStatusLoading ? (
              <Badge variant="secondary" className="text-xs">
                Loading Shopify…
              </Badge>
            ) : shopifyStatus ? (
              <>
                <Badge variant="outline" className="gap-1 text-xs">
                  <Package className="size-3" />
                  {shopifyStatus.products.toLocaleString()} products
                </Badge>
                <Badge variant="outline" className="gap-1 text-xs">
                  <ShoppingCart className="size-3" />
                  {shopifyStatus.orders.toLocaleString()} orders
                </Badge>
                <Badge variant="outline" className="gap-1 text-xs">
                  <Users className="size-3" />
                  {shopifyStatus.customers.toLocaleString()} customers
                </Badge>
              </>
            ) : null}
          </div>
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
