import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Loader2, Package, ShoppingBag } from "lucide-react"

import { CardCarousel } from "@/components/CardCarousel"
import { ProductImage } from "@/components/ProductImage"
import { ShopifyProductCard } from "@/components/ShopifyProductCard"
import { ShopifyProductSearch } from "@/components/ShopifyProductSearch"
import { ShopifySameCategorySection } from "@/components/ShopifySameCategorySection"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  fetchShopifyBoughtTogether,
  fetchShopifyProduct,
} from "@/lib/api"
import type { ShopifyProductSummary } from "@/types/api"

function ProductDetailSkeleton() {
  return (
    <Card className="shadow-none">
      <CardContent className="grid gap-4 p-4 sm:grid-cols-[200px_minmax(0,1fr)]">
        <Skeleton className="aspect-square w-full rounded-lg" />
        <div className="space-y-3">
          <Skeleton className="h-7 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-20 w-full" />
        </div>
      </CardContent>
    </Card>
  )
}

function RecommendationsSkeleton() {
  return (
    <div className="flex gap-3 overflow-hidden">
      {Array.from({ length: 4 }).map((_, index) => (
        <Skeleton key={index} className="h-56 w-44 shrink-0 rounded-xl" />
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

        {detail && (
          <Card className="shadow-none">
            <CardContent className="grid gap-6 p-4 sm:grid-cols-[220px_minmax(0,1fr)]">
              <div className="overflow-hidden rounded-lg border bg-muted/20">
                <ProductImage src={detail.image_url} alt={detail.title} />
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold leading-tight">{detail.title}</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {detail.price && <Badge variant="secondary">${detail.price}</Badge>}
                    {detail.sku && (
                      <Badge variant="outline" className="font-mono">
                        {detail.sku}
                      </Badge>
                    )}
                    {detail.vendor && <Badge variant="outline">{detail.vendor}</Badge>}
                    {detail.product_type && <Badge variant="outline">{detail.product_type}</Badge>}
                    {detail.status && <Badge variant="outline">{detail.status}</Badge>}
                  </div>
                </div>

                {detail.description && (
                  <div
                    className="prose prose-sm max-w-none text-muted-foreground [&_p]:my-2"
                    dangerouslySetInnerHTML={{ __html: detail.description }}
                  />
                )}

                {detail.tags && detail.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {detail.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-[10px]">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}

                {detail.variants && detail.variants.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Variants
                    </p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {detail.variants.slice(0, 6).map((variant) => (
                        <div
                          key={variant.id ?? variant.sku ?? variant.title}
                          className="rounded-md border bg-muted/20 px-3 py-2 text-sm"
                        >
                          <p className="font-medium">{variant.title ?? "Default"}</p>
                          <p className="text-xs text-muted-foreground">
                            {[variant.sku, variant.price ? `$${variant.price}` : null]
                              .filter(Boolean)
                              .join(" · ")}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {selectedProduct && (
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <Package className="size-4 text-muted-foreground" />
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                People also bought this
              </h3>
              {boughtTogetherQuery.isFetching && (
                <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
              )}
            </div>

            {boughtTogetherQuery.isLoading ? (
              <RecommendationsSkeleton />
            ) : boughtTogetherQuery.data?.items.length ? (
              <CardCarousel slideClassName="w-44 shrink-0 basis-44 snap-start" ariaLabel="People also bought">
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
            categoryLabel={detail?.product_type}
            onSelectProduct={setSelectedProduct}
          />
        )}
      </div>
    </main>
  )
}
