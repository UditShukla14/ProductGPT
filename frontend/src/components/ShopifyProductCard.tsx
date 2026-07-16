import { ProductImage } from "@/components/ProductImage"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { ShopifyProductSummary } from "@/types/api"

interface ShopifyProductCardProps {
  product: ShopifyProductSummary
  subtitle?: string | null
  onClick?: (product: ShopifyProductSummary) => void
  className?: string
  /** Hide price badges (required for chat citations). */
  hidePrice?: boolean
}

function CardBody({
  product,
  subtitle,
  hidePrice = false,
}: {
  product: ShopifyProductSummary
  subtitle?: string | null
  hidePrice?: boolean
}) {
  return (
    <>
      <div className="aspect-square w-full shrink-0 overflow-hidden rounded-md border bg-muted/30">
        <ProductImage
          src={product.image_url}
          alt={product.title}
          imageClassName="size-full object-contain p-1.5"
        />
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-1.5 p-3 pt-2">
        <p className="line-clamp-2 min-h-10 text-sm font-medium leading-5">{product.title}</p>

        <div className="flex min-h-5 flex-wrap items-center gap-1">
          {!hidePrice && product.price && (
            <Badge variant="secondary" className="shrink-0 text-[10px]">
              ${product.price}
            </Badge>
          )}
          {product.sku && (
            <Badge variant="outline" className="max-w-full truncate font-mono text-[10px]">
              {product.sku}
            </Badge>
          )}
        </div>

        {subtitle && (
          <p className="mt-auto truncate text-[11px] text-muted-foreground">{subtitle}</p>
        )}
      </div>
    </>
  )
}

export function ShopifyProductCard({
  product,
  subtitle,
  onClick,
  className,
  hidePrice = false,
}: ShopifyProductCardProps) {
  const isClickable = onClick != null

  if (!isClickable) {
    return (
      <Card className={cn("flex h-full flex-col gap-0 py-0 shadow-none", className)}>
        <CardContent className="flex h-full flex-col p-0">
          <CardBody product={product} subtitle={subtitle} hidePrice={hidePrice} />
        </CardContent>
      </Card>
    )
  }

  return (
    <button
      type="button"
      onClick={() => onClick(product)}
      className={cn(
        "flex h-full w-full flex-col overflow-hidden rounded-xl border bg-card text-left transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        className
      )}
    >
      <CardBody product={product} subtitle={subtitle} hidePrice={hidePrice} />
    </button>
  )
}
