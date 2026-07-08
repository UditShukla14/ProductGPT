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
}

export function ShopifyProductCard({
  product,
  subtitle,
  onClick,
  className,
}: ShopifyProductCardProps) {
  const isClickable = onClick != null

  const content = (
    <>
      <div className="aspect-square w-full overflow-hidden rounded-md border bg-muted/30">
        <ProductImage src={product.image_url} alt={product.title} />
      </div>
      <div className="space-y-1">
        <p className="line-clamp-2 text-sm font-medium leading-snug">{product.title}</p>
        <div className="flex flex-wrap items-center gap-1">
          {product.price && (
            <Badge variant="secondary" className="text-[10px]">
              ${product.price}
            </Badge>
          )}
          {product.sku && (
            <Badge variant="outline" className="font-mono text-[10px]">
              {product.sku}
            </Badge>
          )}
        </div>
        {subtitle && <p className="text-[11px] text-muted-foreground">{subtitle}</p>}
      </div>
    </>
  )

  if (!isClickable) {
    return (
      <Card className={cn("h-full gap-0 py-0 shadow-none", className)}>
        <CardContent className="space-y-2 p-3">{content}</CardContent>
      </Card>
    )
  }

  return (
    <button
      type="button"
      onClick={() => onClick(product)}
      className={cn(
        "h-full rounded-xl border bg-card text-left transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        className
      )}
    >
      <div className="space-y-2 p-3">{content}</div>
    </button>
  )
}
