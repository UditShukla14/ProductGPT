import { useEffect, useRef, useState } from "react"
import { useInfiniteQuery } from "@tanstack/react-query"
import { Loader2, Search, Sparkles } from "lucide-react"

import { AppHeader } from "@/components/AppHeader"
import { BoughtTogetherMatchupsModal } from "@/components/BoughtTogetherMatchupsModal"
import { BoughtTogetherSection } from "@/components/BoughtTogetherSection"
import { CardCarousel } from "@/components/CardCarousel"
import { SystemCard } from "@/components/SystemCard"
import { SystemDetailModal } from "@/components/SystemDetailModal"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { EQUIPMENT_CATEGORY_OPTIONS, REFRIGERANT_OPTIONS, componentTypeLabel } from "@/constants/hvac"
import { fetchComponentSearch, fetchRecommendations } from "@/lib/api"
import type {
  BoughtTogetherItem,
  ComponentSearchRequest,
  ComponentType,
  HvacRecommendation,
  HvacRecommendationRequest,
} from "@/types/api"

const PAGE_SIZE = 25

type SearchMode = "criteria" | "product"

type SearchForm = Omit<HvacRecommendationRequest, "limit" | "offset">

type ProductSearchForm = {
  model: string
  component_type: ComponentType
  equipment_category?: string
  refrigerant_type?: string
  prefer_higher_seer: boolean
}

const defaultForm: SearchForm = {
  tonnage: 2,
  min_seer: 15,
  equipment_category: "AC",
  refrigerant_type: "R-32",
  prefer_higher_seer: true,
}

const defaultProductForm: ProductSearchForm = {
  model: "",
  component_type: "auto",
  prefer_higher_seer: true,
}

function buildSearchPayload(form: SearchForm): HvacRecommendationRequest {
  return {
    tonnage: form.tonnage || undefined,
    min_seer: form.min_seer || undefined,
    max_seer: form.max_seer || undefined,
    equipment_category: form.equipment_category || undefined,
    refrigerant_type: form.refrigerant_type || undefined,
    query: form.query || undefined,
    prefer_higher_seer: form.prefer_higher_seer,
  }
}

function SectionHeading({
  title,
  detail,
  count,
}: {
  title: string
  detail?: string
  count?: string
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </h2>
        {detail && <p className="mt-0.5 truncate text-xs text-muted-foreground">{detail}</p>}
      </div>
      {count && <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{count}</span>}
    </div>
  )
}

export default function App() {
  const [form, setForm] = useState<SearchForm>(defaultForm)
  const [productForm, setProductForm] = useState<ProductSearchForm>(defaultProductForm)
  const [activeMode, setActiveMode] = useState<SearchMode | null>(null)
  const [activeSearch, setActiveSearch] = useState<HvacRecommendationRequest | null>(null)
  const [activeProductSearch, setActiveProductSearch] = useState<ComponentSearchRequest | null>(
    null
  )
  const [searchKey, setSearchKey] = useState(0)
  const [productSearchKey, setProductSearchKey] = useState(0)
  const [selected, setSelected] = useState<{
    recommendation: HvacRecommendation
    rank: number
  } | null>(null)
  const [pairedMatchupItem, setPairedMatchupItem] = useState<BoughtTogetherItem | null>(null)
  const activeSearchRef = useRef<HvacRecommendationRequest | null>(null)
  const activeProductSearchRef = useRef<ComponentSearchRequest | null>(null)
  const loadMoreRef = useRef<HTMLDivElement>(null)
  const productLoadMoreRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const header = document.getElementById("app-header")
    if (!header) return

    function updateHeaderHeight() {
      document.documentElement.style.setProperty(
        "--app-header-height",
        `${header!.offsetHeight}px`
      )
    }

    updateHeaderHeight()
    const observer = new ResizeObserver(updateHeaderHeight)
    observer.observe(header)
    return () => observer.disconnect()
  }, [])

  const criteriaQuery = useInfiniteQuery({
    queryKey: ["recommendations", searchKey],
    queryFn: ({ pageParam }) =>
      fetchRecommendations({
        ...activeSearchRef.current!,
        limit: PAGE_SIZE,
        offset: pageParam,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) =>
      lastPage.meta.has_more ? lastPage.meta.offset + lastPage.meta.returned : undefined,
    enabled: activeMode === "criteria" && activeSearch !== null,
  })

  const productQuery = useInfiniteQuery({
    queryKey: ["component-search", productSearchKey],
    queryFn: ({ pageParam }) =>
      fetchComponentSearch({
        ...activeProductSearchRef.current!,
        limit: PAGE_SIZE,
        offset: pageParam,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) =>
      lastPage.meta.has_more ? lastPage.meta.offset + lastPage.meta.returned : undefined,
    enabled: activeMode === "product" && activeProductSearch !== null,
  })

  const {
    data: criteriaData,
    isFetching: isCriteriaFetching,
    isError: isCriteriaError,
    error: criteriaError,
    fetchNextPage: fetchNextCriteriaPage,
    hasNextPage: hasNextCriteriaPage,
    isFetchingNextPage: isFetchingNextCriteriaPage,
  } = criteriaQuery

  const {
    data: productData,
    isFetching: isProductFetching,
    isError: isProductError,
    error: productError,
    fetchNextPage: fetchNextProductPage,
    hasNextPage: hasNextProductPage,
    isFetchingNextPage: isFetchingNextProductPage,
  } = productQuery

  useEffect(() => {
    const target = loadMoreRef.current
    if (!target || !hasNextCriteriaPage || isFetchingNextCriteriaPage || isCriteriaFetching) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) fetchNextCriteriaPage()
      },
      { rootMargin: "200px" }
    )

    observer.observe(target)
    return () => observer.disconnect()
  }, [
    fetchNextCriteriaPage,
    hasNextCriteriaPage,
    isFetchingNextCriteriaPage,
    isCriteriaFetching,
    criteriaData,
  ])

  useEffect(() => {
    const target = productLoadMoreRef.current
    if (!target || !hasNextProductPage || isFetchingNextProductPage || isProductFetching) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) fetchNextProductPage()
      },
      { rootMargin: "200px" }
    )

    observer.observe(target)
    return () => observer.disconnect()
  }, [
    fetchNextProductPage,
    hasNextProductPage,
    isFetchingNextProductPage,
    isProductFetching,
    productData,
  ])

  function updateField<K extends keyof SearchForm>(key: K, value: SearchForm[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function updateProductField<K extends keyof ProductSearchForm>(
    key: K,
    value: ProductSearchForm[K]
  ) {
    setProductForm((current) => ({ ...current, [key]: value }))
  }

  function handleCriteriaSubmit(event: React.FormEvent) {
    event.preventDefault()
    const payload = buildSearchPayload(form)
    activeSearchRef.current = payload
    setActiveSearch(payload)
    setActiveMode("criteria")
    setSearchKey((key) => key + 1)
    setSelected(null)
  }

  function handleProductSubmit(event: React.FormEvent) {
    event.preventDefault()
    const model = productForm.model.trim()
    if (!model) return

    const payload: ComponentSearchRequest = {
      model,
      component_type: productForm.component_type,
      equipment_category: productForm.equipment_category,
      refrigerant_type: productForm.refrigerant_type,
      prefer_higher_seer: productForm.prefer_higher_seer,
    }
    activeProductSearchRef.current = payload
    setActiveProductSearch(payload)
    setActiveMode("product")
    setProductSearchKey((key) => key + 1)
    setSelected(null)
    setPairedMatchupItem(null)
  }

  const recommendations: HvacRecommendation[] =
    criteriaData?.pages.flatMap((page) => page.recommendations) ?? []
  const criteriaMeta = criteriaData?.pages[criteriaData.pages.length - 1]?.meta
  const criteriaTotal = criteriaMeta?.total_ranked ?? 0

  const productFirstPage = productData?.pages[0]
  const productMatchups: HvacRecommendation[] =
    productData?.pages.flatMap((page) => page.similar_matchups) ?? []
  const boughtTogether = productFirstPage?.bought_together ?? []
  const productMeta = productData?.pages[productData.pages.length - 1]?.meta
  const productTotal = productMeta?.total_matchups ?? 0
  const matchedType = productFirstPage?.matched_type ?? null
  const matchedModel = productFirstPage?.matched_model ?? activeProductSearch?.model ?? null
  const pairedAnchorType = matchedType ?? productForm.component_type
  const canShowPairedMatchups =
    pairedAnchorType !== "auto" && matchedModel != null && matchedModel.length > 0

  const hasSearched = activeMode !== null
  const isCriteriaMode = activeMode === "criteria"
  const isProductMode = activeMode === "product"
  const isInitialCriteriaLoading =
    isCriteriaMode && isCriteriaFetching && recommendations.length === 0
  const isInitialProductLoading = isProductMode && isProductFetching && productMatchups.length === 0

  return (
    <div className="min-h-svh bg-background">
      <AppHeader
        productModel={productForm.model}
        componentType={productForm.component_type}
        equipmentCategory={productForm.equipment_category}
        refrigerantType={productForm.refrigerant_type}
        preferHigherSeer={productForm.prefer_higher_seer}
        isProductSearching={isInitialProductLoading}
        onProductModelChange={(value) => updateProductField("model", value)}
        onComponentTypeChange={(value) => updateProductField("component_type", value)}
        onEquipmentCategoryChange={(value) => updateProductField("equipment_category", value)}
        onRefrigerantTypeChange={(value) => updateProductField("refrigerant_type", value)}
        onPreferHigherSeerChange={(value) => updateProductField("prefer_higher_seer", value)}
        onProductSubmit={handleProductSubmit}
      />

      <main className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
        <div className="grid gap-4 lg:grid-cols-[280px_1fr] lg:items-start">
          <aside className="lg:sticky lg:top-[calc(var(--app-header-height,10rem)+0.75rem)] lg:self-start">
            <Card className="gap-0 py-0 shadow-none">
              <CardHeader className="gap-1 px-4 py-3">
                <CardTitle className="flex items-center gap-1.5 text-sm">
                  <Search className="size-3.5" />
                  System criteria
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <form className="space-y-3" onSubmit={handleCriteriaSubmit}>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="col-span-2 space-y-1">
                      <Label htmlFor="tonnage" className="text-[11px] text-muted-foreground">
                        Tonnage
                      </Label>
                      <Select
                        id="tonnage"
                        value={String(form.tonnage ?? "")}
                        onChange={(event) =>
                          updateField("tonnage", Number(event.target.value) || undefined)
                        }
                        className="h-8 text-sm"
                      >
                        <option value="">Any</option>
                        {[1.5, 2, 2.5, 3, 3.5, 4, 5].map((value) => (
                          <option key={value} value={value}>
                            {value} Ton
                          </option>
                        ))}
                      </Select>
                    </div>

                    <div className="space-y-1">
                      <Label htmlFor="min_seer" className="text-[11px] text-muted-foreground">
                        Min SEER
                      </Label>
                      <Input
                        id="min_seer"
                        type="number"
                        step="0.1"
                        min={0}
                        placeholder="15"
                        value={form.min_seer ?? ""}
                        onChange={(event) =>
                          updateField("min_seer", Number(event.target.value) || undefined)
                        }
                        className="h-8 text-sm"
                      />
                    </div>

                    <div className="space-y-1">
                      <Label htmlFor="max_seer" className="text-[11px] text-muted-foreground">
                        Max SEER
                      </Label>
                      <Input
                        id="max_seer"
                        type="number"
                        step="0.1"
                        min={0}
                        placeholder="Any"
                        value={form.max_seer ?? ""}
                        onChange={(event) =>
                          updateField("max_seer", Number(event.target.value) || undefined)
                        }
                        className="h-8 text-sm"
                      />
                    </div>

                    <div className="col-span-2 space-y-1">
                      <Label htmlFor="equipment_category" className="text-[11px] text-muted-foreground">
                        Category
                      </Label>
                      <Select
                        id="equipment_category"
                        value={form.equipment_category ?? ""}
                        onChange={(event) =>
                          updateField("equipment_category", event.target.value || undefined)
                        }
                        className="h-8 text-sm"
                      >
                        <option value="">Any</option>
                        {EQUIPMENT_CATEGORY_OPTIONS.map((value) => (
                          <option key={value} value={value}>
                            {value}
                          </option>
                        ))}
                      </Select>
                    </div>

                    <div className="col-span-2 space-y-1">
                      <Label htmlFor="refrigerant_type" className="text-[11px] text-muted-foreground">
                        Refrigerant
                      </Label>
                      <Select
                        id="refrigerant_type"
                        value={form.refrigerant_type ?? ""}
                        onChange={(event) =>
                          updateField("refrigerant_type", event.target.value || undefined)
                        }
                        className="h-8 text-sm"
                      >
                        <option value="">Any</option>
                        {REFRIGERANT_OPTIONS.map((value) => (
                          <option key={value} value={value}>
                            {value}
                          </option>
                        ))}
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <Label htmlFor="query" className="text-[11px] text-muted-foreground">
                      Search hint
                    </Label>
                    <Input
                      id="query"
                      placeholder="modulating, ECM…"
                      value={form.query ?? ""}
                      onChange={(event) => updateField("query", event.target.value || undefined)}
                      className="h-8 text-sm"
                    />
                  </div>

                  <div className="flex items-center justify-between rounded-md border px-2.5 py-1.5">
                    <Label htmlFor="criteria_prefer_seer" className="text-xs">
                      Prefer higher SEER
                    </Label>
                    <Switch
                      id="criteria_prefer_seer"
                      checked={form.prefer_higher_seer ?? true}
                      onCheckedChange={(checked) => updateField("prefer_higher_seer", checked)}
                    />
                  </div>

                  <Button
                    type="submit"
                    size="sm"
                    className="h-8 w-full"
                    disabled={isInitialCriteriaLoading}
                  >
                    {isInitialCriteriaLoading ? (
                      <>
                        <Loader2 className="animate-spin" />
                        Finding…
                      </>
                    ) : (
                      <>
                        <Sparkles />
                        Recommend
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </aside>

          <section className="space-y-4">
            {isCriteriaMode && (
              <>
                <SectionHeading
                  title="Recommended systems"
                  detail={`${PAGE_SIZE} per batch`}
                  count={
                    criteriaMeta
                      ? `${recommendations.length} / ${criteriaTotal}`
                      : undefined
                  }
                />

                {isCriteriaError && (
                  <Alert variant="destructive" className="py-2">
                    <AlertTitle className="text-sm">Could not load recommendations</AlertTitle>
                    <AlertDescription className="text-xs">
                      {criteriaError instanceof Error ? criteriaError.message : "Unknown error"}
                    </AlertDescription>
                  </Alert>
                )}

                {isInitialCriteriaLoading && (
                  <div className="space-y-2">
                    {[1, 2, 3].map((item) => (
                      <Skeleton key={item} className="h-24 w-full rounded-lg" />
                    ))}
                  </div>
                )}

                {!isInitialCriteriaLoading && recommendations.length === 0 && !isCriteriaError && (
                  <Alert className="py-2">
                    <AlertTitle className="text-sm">No matches</AlertTitle>
                    <AlertDescription className="text-xs">
                      Relax SEER, category, or refrigerant filters.
                    </AlertDescription>
                  </Alert>
                )}

                {recommendations.length > 0 && (
                  <div className="space-y-2 overflow-visible">
                    {recommendations.map((recommendation, index) => (
                      <SystemCard
                        key={recommendation.system.id}
                        recommendation={recommendation}
                        rank={index + 1}
                        onClick={() => setSelected({ recommendation, rank: index + 1 })}
                      />
                    ))}
                  </div>
                )}

                {recommendations.length > 0 && (
                  <div ref={loadMoreRef} className="flex justify-center py-2">
                    {isFetchingNextCriteriaPage ? (
                      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Loader2 className="size-3.5 animate-spin" />
                        Loading…
                      </span>
                    ) : hasNextCriteriaPage ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => fetchNextCriteriaPage()}
                      >
                        Load {PAGE_SIZE} more
                      </Button>
                    ) : (
                      <span className="text-xs text-muted-foreground">All loaded</span>
                    )}
                  </div>
                )}
              </>
            )}

            {isProductMode && (
              <>
                <SectionHeading
                  title="Product search"
                  detail={
                    matchedModel
                      ? `${componentTypeLabel(matchedType)} · ${matchedModel}`
                      : `Model ${productFirstPage?.query ?? productForm.model}`
                  }
                  count={
                    productMeta
                      ? `${productTotal} matchup${productTotal === 1 ? "" : "s"}`
                      : undefined
                  }
                />

                {isProductError && (
                  <Alert variant="destructive" className="py-2">
                    <AlertTitle className="text-sm">Search failed</AlertTitle>
                    <AlertDescription className="text-xs">
                      {productError instanceof Error ? productError.message : "Unknown error"}
                    </AlertDescription>
                  </Alert>
                )}

                {isInitialProductLoading && (
                  <div className="flex gap-3">
                    {[1, 2].map((item) => (
                      <Skeleton key={item} className="h-28 w-64 shrink-0 rounded-lg" />
                    ))}
                  </div>
                )}

                {!isInitialProductLoading && productMatchups.length === 0 && !isProductError && (
                  <Alert className="py-2">
                    <AlertTitle className="text-sm">No matchups</AlertTitle>
                    <AlertDescription className="text-xs">
                      Check model spelling or try auto-detect.
                    </AlertDescription>
                  </Alert>
                )}

                {!isInitialProductLoading && boughtTogether.length > 0 && (
                  <BoughtTogetherSection
                    items={boughtTogether}
                    searchedType={matchedType}
                    onItemClick={
                      canShowPairedMatchups ? (item) => setPairedMatchupItem(item) : undefined
                    }
                  />
                )}

                {!isInitialProductLoading && productMatchups.length > 0 && (
                  <>
                    <SectionHeading title="Similar matchups" />

                    <CardCarousel
                      ariaLabel="Similar matchups"
                      slideClassName="w-[min(100%,18rem)] sm:w-[20rem]"
                    >
                      {productMatchups.map((recommendation, index) => (
                        <SystemCard
                          key={recommendation.system.id}
                          recommendation={recommendation}
                          rank={index + 1}
                          onClick={() => setSelected({ recommendation, rank: index + 1 })}
                        />
                      ))}
                    </CardCarousel>

                    <div ref={productLoadMoreRef} className="flex justify-center py-2">
                      {isFetchingNextProductPage ? (
                        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Loader2 className="size-3.5 animate-spin" />
                          Loading…
                        </span>
                      ) : hasNextProductPage ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => fetchNextProductPage()}
                        >
                          Load {PAGE_SIZE} more
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">All loaded</span>
                      )}
                    </div>
                  </>
                )}
              </>
            )}

            {!hasSearched && (
              <Card className="border-dashed py-0 shadow-none">
                <CardContent className="flex min-h-32 flex-col items-center justify-center gap-1.5 py-8 text-center">
                  <Sparkles className="size-5 text-muted-foreground" />
                  <p className="text-sm font-medium">Start a search</p>
                  <p className="max-w-sm text-xs text-muted-foreground">
                    Use criteria filters or search by model number in the header.
                  </p>
                </CardContent>
              </Card>
            )}

            <BoughtTogetherMatchupsModal
              open={pairedMatchupItem != null && canShowPairedMatchups}
              onClose={() => setPairedMatchupItem(null)}
              anchorType={pairedAnchorType as "outdoor" | "coil" | "furnace"}
              anchorModel={matchedModel ?? ""}
              item={pairedMatchupItem}
              equipmentCategory={activeProductSearch?.equipment_category}
              refrigerantType={activeProductSearch?.refrigerant_type}
              preferHigherSeer={productForm.prefer_higher_seer}
              onSelectMatchup={(recommendation, rank) => {
                setPairedMatchupItem(null)
                setSelected({ recommendation, rank })
              }}
            />

            <SystemDetailModal
              open={selected != null}
              recommendation={selected?.recommendation ?? null}
              rank={selected?.rank ?? 0}
              onClose={() => setSelected(null)}
            />
          </section>
        </div>
      </main>
    </div>
  )
}
