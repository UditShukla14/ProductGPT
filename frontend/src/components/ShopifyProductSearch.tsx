import { useEffect, useId, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Loader2, Search } from "lucide-react"

import { ProductImage } from "@/components/ProductImage"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { searchShopifyProducts } from "@/lib/api"
import type { ShopifyProductSummary } from "@/types/api"

interface ShopifyProductSearchProps {
  selectedId?: string | null
  onSelect: (product: ShopifyProductSummary) => void
}

export function ShopifyProductSearch({ selectedId, onSelect }: ShopifyProductSearchProps) {
  const listboxId = useId()
  const containerRef = useRef<HTMLDivElement>(null)
  const [query, setQuery] = useState("")
  const [debouncedQuery, setDebouncedQuery] = useState("")
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 250)
    return () => window.clearTimeout(timer)
  }, [query])

  const { data, isFetching, isError, error } = useQuery({
    queryKey: ["shopify-product-search", debouncedQuery],
    queryFn: () => searchShopifyProducts(debouncedQuery, 10),
    enabled: debouncedQuery.length >= 2,
    staleTime: 30_000,
  })

  const results = data?.results ?? []

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handlePointerDown)
    return () => document.removeEventListener("mousedown", handlePointerDown)
  }, [])

  useEffect(() => {
    setActiveIndex(-1)
  }, [debouncedQuery, results.length])

  function selectProduct(product: ShopifyProductSummary) {
    setQuery(product.title)
    setOpen(false)
    onSelect(product)
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (!open && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      setOpen(true)
      return
    }

    if (event.key === "ArrowDown") {
      event.preventDefault()
      if (results.length === 0) return
      setActiveIndex((index) => (index + 1) % results.length)
      return
    }

    if (event.key === "ArrowUp") {
      event.preventDefault()
      if (results.length === 0) return
      setActiveIndex((index) => (index <= 0 ? results.length - 1 : index - 1))
      return
    }

    if (event.key === "Enter" && activeIndex >= 0 && results[activeIndex]) {
      event.preventDefault()
      selectProduct(results[activeIndex])
      return
    }

    if (event.key === "Escape") {
      setOpen(false)
    }
  }

  const showDropdown = open && debouncedQuery.length >= 2

  return (
    <div ref={containerRef} className="relative w-full max-w-2xl">
      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search by title, SKU, tag, or product id…"
          className="pl-9"
          role="combobox"
          aria-expanded={showDropdown}
          aria-controls={listboxId}
          aria-activedescendant={
            activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined
          }
          autoComplete="off"
        />
        {isFetching && (
          <Loader2 className="absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />
        )}
      </div>

      {showDropdown && (
        <div
          id={listboxId}
          role="listbox"
          className="absolute z-50 mt-1 max-h-80 w-full overflow-y-auto rounded-lg border bg-popover p-1 shadow-md"
        >
          {isError ? (
            <p className="px-3 py-2 text-sm text-destructive">
              {error instanceof Error ? error.message : "Search failed"}
            </p>
          ) : results.length === 0 && !isFetching ? (
            <p className="px-3 py-2 text-sm text-muted-foreground">No products found</p>
          ) : (
            results.map((product, index) => (
              <button
                key={product.id}
                id={`${listboxId}-option-${index}`}
                type="button"
                role="option"
                aria-selected={selectedId === product.id || index === activeIndex}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => selectProduct(product)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-md px-2 py-2 text-left text-sm transition-colors",
                  index === activeIndex ? "bg-accent text-accent-foreground" : "hover:bg-muted/60"
                )}
              >
                <div className="size-10 shrink-0 overflow-hidden rounded-md border bg-muted/30">
                  <ProductImage
                    src={product.image_url}
                    alt={product.title}
                    imageClassName="size-10 object-contain p-0.5"
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{product.title}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {[product.sku, product.vendor, product.product_type].filter(Boolean).join(" · ")}
                  </p>
                </div>
                {product.price && (
                  <span className="shrink-0 text-xs font-medium text-muted-foreground">
                    ${product.price}
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
