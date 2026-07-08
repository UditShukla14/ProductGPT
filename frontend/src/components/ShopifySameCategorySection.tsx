import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Layers, Loader2 } from "lucide-react"

import { CardCarousel } from "@/components/CardCarousel"
import { ShopifyProductCard } from "@/components/ShopifyProductCard"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { fetchShopifySameCategory } from "@/lib/api"
import type { ShopifyProductSummary } from "@/types/api"

function RecommendationsSkeleton() {
  return (
    <div className="flex gap-3 overflow-hidden">
      {Array.from({ length: 4 }).map((_, index) => (
        <Skeleton key={index} className="h-56 w-44 shrink-0 rounded-xl" />
      ))}
    </div>
  )
}

interface ShopifySameCategorySectionProps {
  productId: string
  categoryLabel?: string | null
  onSelectProduct: (product: ShopifyProductSummary) => void
}

export function ShopifySameCategorySection({
  productId,
  categoryLabel,
  onSelectProduct,
}: ShopifySameCategorySectionProps) {
  const [activeBrand, setActiveBrand] = useState<string | null>(null)

  const sameCategoryQuery = useQuery({
    queryKey: ["shopify-same-category", productId],
    queryFn: () => fetchShopifySameCategory(productId),
    enabled: Boolean(productId),
  })

  const brands = sameCategoryQuery.data?.brands ?? []

  useEffect(() => {
    setActiveBrand(sameCategoryQuery.data?.brands[0]?.vendor ?? null)
  }, [productId, sameCategoryQuery.data])

  const activeGroup = brands.find((brand) => brand.vendor === activeBrand) ?? brands[0]

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Layers className="size-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Other options in the same category
        </h3>
        {categoryLabel && (
          <span className="text-xs text-muted-foreground">({categoryLabel})</span>
        )}
        {sameCategoryQuery.isFetching && (
          <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
        )}
      </div>

      {sameCategoryQuery.isLoading ? (
        <RecommendationsSkeleton />
      ) : brands.length === 0 ? (
        <Card className="shadow-none">
          <CardHeader className="py-4">
            <CardTitle className="text-sm font-normal text-muted-foreground">
              No other products found in this category from other brands.
            </CardTitle>
          </CardHeader>
        </Card>
      ) : (
        <>
          <div className="flex gap-1 overflow-x-auto rounded-lg border bg-muted/40 p-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {brands.map((brand) => {
              const isActive = brand.vendor === activeGroup?.vendor
              return (
                <button
                  key={brand.vendor}
                  type="button"
                  onClick={() => setActiveBrand(brand.vendor)}
                  className={cn(
                    "shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    isActive
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {brand.vendor}
                  <span className="ml-1 text-[10px] text-muted-foreground">
                    ({brand.products.length})
                  </span>
                </button>
              )
            })}
          </div>

          {activeGroup && activeGroup.products.length > 0 ? (
            <CardCarousel
              key={activeGroup.vendor}
              slideClassName="w-44 shrink-0 basis-44 snap-start"
              ariaLabel={`${activeGroup.vendor} products in same category`}
            >
              {activeGroup.products.map((product) => (
                <ShopifyProductCard
                  key={product.id}
                  product={product}
                  subtitle={activeGroup.vendor}
                  onClick={onSelectProduct}
                />
              ))}
            </CardCarousel>
          ) : (
            <Card className="shadow-none">
              <CardHeader className="py-4">
                <CardTitle className="text-sm font-normal text-muted-foreground">
                  No products found for {activeGroup?.vendor ?? "this brand"}.
                </CardTitle>
              </CardHeader>
            </Card>
          )}
        </>
      )}
    </section>
  )
}
