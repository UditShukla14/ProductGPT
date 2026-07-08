import { BadgeCheck, CircleSlash, Package2, Tag } from "lucide-react"

import { ProductImage } from "@/components/ProductImage"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import type { ShopifyProductDetail as ShopifyProductDetailType } from "@/types/api"

interface ShopifyProductDetailProps {
  detail: ShopifyProductDetailType
}

function AttributeRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2">
      <dt className="shrink-0 text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="min-w-0 truncate text-right text-sm font-medium">{value}</dd>
    </div>
  )
}

export function ShopifyProductDetail({ detail }: ShopifyProductDetailProps) {
  const available = detail.available_for_sale
  const inventory = detail.inventory_quantity
  const attributes: { label: string; value: React.ReactNode }[] = []

  if (detail.vendor) attributes.push({ label: "Brand", value: detail.vendor })
  if (detail.product_type) attributes.push({ label: "Category", value: detail.product_type })
  if (detail.sku)
    attributes.push({ label: "SKU", value: <span className="font-mono">{detail.sku}</span> })
  if (detail.status)
    attributes.push({ label: "Status", value: <span className="capitalize">{detail.status}</span> })
  if (typeof inventory === "number")
    attributes.push({ label: "Inventory", value: `${inventory.toLocaleString()} in stock` })

  return (
    <article className="overflow-hidden rounded-xl border bg-card">
      <div className="grid gap-0 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
        <div className="border-b bg-muted/20 p-6 lg:border-b-0 lg:border-r">
          <div className="mx-auto aspect-square w-full max-w-sm overflow-hidden rounded-lg border bg-background">
            <ProductImage
              src={detail.image_url}
              alt={detail.title}
              imageClassName="size-full object-contain p-4"
            />
          </div>
        </div>

        <div className="flex min-w-0 flex-col gap-5 p-6">
          <header className="space-y-2">
            {detail.vendor && (
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {detail.vendor}
              </p>
            )}
            <h2 className="text-2xl font-semibold leading-tight tracking-tight">{detail.title}</h2>

            <div className="flex flex-wrap items-center gap-3 pt-1">
              {detail.price && (
                <span className="text-2xl font-semibold tabular-nums">${detail.price}</span>
              )}
              {typeof available === "boolean" && (
                <Badge
                  variant="outline"
                  className={cn(
                    "gap-1",
                    available
                      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                      : "border-muted-foreground/20 bg-muted text-muted-foreground"
                  )}
                >
                  {available ? (
                    <BadgeCheck className="size-3.5" />
                  ) : (
                    <CircleSlash className="size-3.5" />
                  )}
                  {available ? "In stock" : "Out of stock"}
                </Badge>
              )}
            </div>
          </header>

          {attributes.length > 0 && (
            <dl className="divide-y rounded-lg border bg-muted/10 px-4">
              {attributes.map((attr) => (
                <AttributeRow key={attr.label} label={attr.label} value={attr.value} />
              ))}
            </dl>
          )}

          {detail.description && (
            <section className="space-y-2">
              <h3 className="text-sm font-semibold tracking-tight">Description</h3>
              <div
                className="prose prose-sm max-w-none text-muted-foreground [&_a]:text-primary [&_img]:rounded-md [&_li]:my-0.5 [&_p]:my-2"
                dangerouslySetInnerHTML={{ __html: detail.description }}
              />
            </section>
          )}

          {detail.variants && detail.variants.length > 0 && (
            <section className="space-y-2">
              <h3 className="flex items-center gap-1.5 text-sm font-semibold tracking-tight">
                <Package2 className="size-4 text-muted-foreground" />
                Variants
                <span className="text-xs font-normal text-muted-foreground">
                  ({detail.variants.length})
                </span>
              </h3>
              <div className="overflow-hidden rounded-lg border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                      <th className="px-3 py-2 font-medium">Variant</th>
                      <th className="px-3 py-2 font-medium">SKU</th>
                      <th className="px-3 py-2 text-right font-medium">Price</th>
                      <th className="px-3 py-2 text-right font-medium">Stock</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {detail.variants.map((variant) => (
                      <tr key={variant.id ?? variant.sku ?? variant.title} className="hover:bg-muted/20">
                        <td className="px-3 py-2 font-medium">{variant.title ?? "Default"}</td>
                        <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                          {variant.sku ?? "—"}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {variant.price ? `$${variant.price}` : "—"}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                          {typeof variant.inventory_quantity === "number"
                            ? variant.inventory_quantity.toLocaleString()
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {detail.tags && detail.tags.length > 0 && (
            <section className="space-y-2">
              <Separator />
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <Tag className="size-3.5 text-muted-foreground" />
                {detail.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-[10px] font-normal">
                    {tag}
                  </Badge>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </article>
  )
}
