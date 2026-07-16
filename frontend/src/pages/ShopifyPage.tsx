import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Loader2, Package, ShoppingBag } from "lucide-react"

import { CardCarousel } from "@/components/CardCarousel"
import { ProductFloatingChat } from "@/components/ProductFloatingChat"
import { ShopifyProductCard } from "@/components/ShopifyProductCard"
import { ShopifyMatchupsSection } from "@/components/ShopifyMatchupsSection"
import { ShopifyProductDetail } from "@/components/ShopifyProductDetail"
import { ShopifyProductSearch } from "@/components/ShopifyProductSearch"
import { ShopifySameCategorySection } from "@/components/ShopifySameCategorySection"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  fetchShopifyBoughtTogether,
  fetchShopifyProduct,
} from "@/lib/api"
import type { ShopifyProductSummary } from "@/types/api"

function ProductDetailSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <div className="grid lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
        <div className="border-b bg-muted/20 p-6 lg:border-b-0 lg:border-r">
          <Skeleton className="mx-auto aspect-square w-full max-w-sm rounded-lg" />
        </div>
        <div className="space-y-4 p-6">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-7 w-28" />
          <Skeleton className="h-32 w-full rounded-lg" />
          <Skeleton className="h-20 w-full" />
        </div>
      </div>
    </div>
  )
}

function RecommendationsSkeleton() {
  return (
    <div className="flex gap-3 overflow-hidden">
      {Array.from({ length: 4 }).map((_, index) => (
        <Skeleton key={index} className="h-72 w-48 shrink-0 rounded-xl" />
      ))}
    </div>
  )
}

export function ShopifyPage() {
  const [selectedProduct, setSelectedProduct] = useState<ShopifyProductSummary | null>(null)

  const productQuery = useQuery({
    queryKey: ["shopify-product", selectedProduct?.id],
    queryFn: () => fetchShopifyProduct(selectedProduct!.id),
    enabled: selectedProduct != null,
  })

  const boughtTogetherQuery = useQuery({
    queryKey: ["shopify-bought-together", selectedProduct?.id],
    queryFn: () => fetchShopifyBoughtTogether(selectedProduct!.id),
    enabled: selectedProduct != null,
  })

  const detail = productQuery.data

  return (
    <main className="mx-auto w-full max-w-7xl min-w-0 px-4 py-6 sm:px-6">
      <div className="space-y-6">
        <section className="space-y-3">
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Product search</h2>
            <p className="text-sm text-muted-foreground">
              Search synced Shopify products, then view details and order-based recommendations.
            </p>
          </div>
          <ShopifyProductSearch
            selectedId={selectedProduct?.id}
            onSelect={(product) => setSelectedProduct(product)}
          />
        </section>

        {!selectedProduct && (
          <Alert>
            <ShoppingBag className="size-4" />
            <AlertTitle>Start with a product search</AlertTitle>
            <AlertDescription>
              Type at least two characters to see matching products in the dropdown.
            </AlertDescription>
          </Alert>
        )}

        {selectedProduct && productQuery.isLoading && <ProductDetailSkeleton />}

        {selectedProduct && productQuery.isError && (
          <Alert variant="destructive">
            <AlertTitle>Could not load product</AlertTitle>
            <AlertDescription>
              {productQuery.error instanceof Error
                ? productQuery.error.message
                : "Unknown error loading product details."}
            </AlertDescription>
          </Alert>
        )}

        {detail && <ShopifyProductDetail detail={detail} />}

        {selectedProduct && <ShopifyMatchupsSection productId={selectedProduct.id} />}

        {selectedProduct && (
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <Package className="size-4 text-muted-foreground" />
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Customers also bought
              </h3>
              {boughtTogetherQuery.isFetching && (
                <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
              )}
            </div>

            {boughtTogetherQuery.isLoading ? (
              <RecommendationsSkeleton />
            ) : boughtTogetherQuery.data?.items.length ? (
              <CardCarousel slideClassName="w-48 shrink-0 basis-48 snap-start" ariaLabel="Customers also bought">
                {boughtTogetherQuery.data.items.map((item) => (
                  <ShopifyProductCard
                    key={item.product.id}
                    product={item.product}
                    subtitle={item.reason ?? undefined}
                    onClick={setSelectedProduct}
                  />
                ))}
              </CardCarousel>
            ) : (
              <Card className="shadow-none">
                <CardHeader className="py-4">
                  <CardTitle className="text-sm font-normal text-muted-foreground">
                    No co-purchase data yet for this product. Sync orders on the server to populate this
                    section.
                  </CardTitle>
                </CardHeader>
              </Card>
            )}
          </section>
        )}

        {selectedProduct && (
          <ShopifySameCategorySection
            productId={selectedProduct.id}
            onSelectProduct={setSelectedProduct}
          />
        )}
      </div>

      {selectedProduct && (
        <ProductFloatingChat
          productId={selectedProduct.id}
          productTitle={detail?.title ?? selectedProduct.title}
        />
      )}
    </main>
  )
}
