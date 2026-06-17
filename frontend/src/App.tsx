import { useEffect, useRef, useState } from "react"
import { useInfiniteQuery } from "@tanstack/react-query"
import { Loader2, Search, Sparkles } from "lucide-react"

import { AppHeader } from "@/components/AppHeader"
import { BoughtTogetherSection } from "@/components/BoughtTogetherSection"
import { SystemCard } from "@/components/SystemCard"
import { SystemDetailModal } from "@/components/SystemDetailModal"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { SYSTEM_TYPE_SEER2_OPTIONS } from "@/constants/hvac"
import { fetchComponentSearch, fetchRecommendations } from "@/lib/api"
import type {
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
  prefer_higher_seer: boolean
}

const defaultForm: SearchForm = {
  tonnage: 2,
  min_seer: 14,
  config: "Horizontal Flow",
  system_type_seer2: "Split System (SEER2) - Gas Heating 15.3 SEER",
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
    config: form.config || undefined,
    system_type_seer2: form.system_type_seer2 || undefined,
    stage: form.stage || undefined,
    indoor_unit: form.indoor_unit || undefined,
    furnace_btu: form.furnace_btu || undefined,
    query: form.query || undefined,
    prefer_higher_seer: form.prefer_higher_seer,
  }
}

function componentTypeLabel(type: ComponentType | null | undefined) {
  if (!type || type === "auto") return "component"
  return type
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
        if (entries[0]?.isIntersecting) {
          fetchNextCriteriaPage()
        }
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
        if (entries[0]?.isIntersecting) {
          fetchNextProductPage()
        }
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
      prefer_higher_seer: productForm.prefer_higher_seer,
    }
    activeProductSearchRef.current = payload
    setActiveProductSearch(payload)
    setActiveMode("product")
    setProductSearchKey((key) => key + 1)
    setSelected(null)
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
  const matchedModel = productFirstPage?.matched_model ?? null

  const hasSearched = activeMode !== null
  const isCriteriaMode = activeMode === "criteria"
  const isProductMode = activeMode === "product"
  const isInitialCriteriaLoading =
    isCriteriaMode && isCriteriaFetching && recommendations.length === 0
  const isInitialProductLoading = isProductMode && isProductFetching && productMatchups.length === 0

  return (
    <div className="min-h-svh bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.08),_transparent_35%)]">
      <AppHeader
        productModel={productForm.model}
        componentType={productForm.component_type}
        preferHigherSeer={productForm.prefer_higher_seer}
        isProductSearching={isInitialProductLoading}
        onProductModelChange={(value) => updateProductField("model", value)}
        onComponentTypeChange={(value) => updateProductField("component_type", value)}
        onPreferHigherSeerChange={(value) => updateProductField("prefer_higher_seer", value)}
        onProductSubmit={handleProductSubmit}
      />

      <main className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[360px_1fr] lg:px-6">
        <div className="lg:sticky lg:top-[calc(var(--app-header-height,12rem)+1.5rem)] lg:self-start">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="size-4" />
                System criteria
              </CardTitle>
              <CardDescription>
                Filter AHRI-certified bundles and rank by efficiency and fit.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleCriteriaSubmit}>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
                  <div className="space-y-2">
                    <Label htmlFor="tonnage">Tonnage</Label>
                    <Select
                      id="tonnage"
                      value={String(form.tonnage ?? "")}
                      onChange={(event) =>
                        updateField("tonnage", Number(event.target.value) || undefined)
                      }
                    >
                      <option value="">Any</option>
                      {[1.5, 2, 2.5, 3, 3.5, 4, 5].map((value) => (
                        <option key={value} value={value}>
                          {value} Ton
                        </option>
                      ))}
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="min_seer">Minimum SEER</Label>
                    <Input
                      id="min_seer"
                      type="number"
                      step="0.1"
                      value={form.min_seer ?? ""}
                      onChange={(event) =>
                        updateField("min_seer", Number(event.target.value) || undefined)
                      }
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="config">Configuration</Label>
                    <Select
                      id="config"
                      value={form.config ?? ""}
                      onChange={(event) => updateField("config", event.target.value || undefined)}
                    >
                      <option value="">Any</option>
                      <option value="Horizontal Flow">Horizontal Flow</option>
                      <option value="Upflow">Upflow</option>
                      <option value="Downflow">Downflow</option>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="system_type_seer2">System type (SEER2)</Label>
                    <Select
                      id="system_type_seer2"
                      value={form.system_type_seer2 ?? ""}
                      onChange={(event) =>
                        updateField("system_type_seer2", event.target.value || undefined)
                      }
                    >
                      <option value="">Any</option>
                      {SYSTEM_TYPE_SEER2_OPTIONS.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="stage">Stage</Label>
                    <Select
                      id="stage"
                      value={form.stage ?? ""}
                      onChange={(event) => updateField("stage", event.target.value || undefined)}
                    >
                      <option value="">Any</option>
                      <option value="SINGLE STAGE">Single Stage</option>
                      <option value="TWO STAGE">Two Stage</option>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="furnace_btu">Furnace BTU</Label>
                    <Input
                      id="furnace_btu"
                      placeholder="e.g. 060"
                      value={form.furnace_btu ?? ""}
                      onChange={(event) =>
                        updateField("furnace_btu", event.target.value || undefined)
                      }
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="query">Search hint</Label>
                  <Input
                    id="query"
                    placeholder="modulating, 96% VS, ECM..."
                    value={form.query ?? ""}
                    onChange={(event) => updateField("query", event.target.value || undefined)}
                  />
                </div>

                <div className="flex items-center justify-between rounded-lg border px-3 py-2">
                  <div>
                    <p className="text-sm font-medium">Prefer higher SEER</p>
                    <p className="text-xs text-muted-foreground">Boost efficient systems in ranking</p>
                  </div>
                  <Switch
                    checked={form.prefer_higher_seer ?? true}
                    onCheckedChange={(checked) => updateField("prefer_higher_seer", checked)}
                  />
                </div>

                <Button type="submit" className="w-full" disabled={isInitialCriteriaLoading}>
                  {isInitialCriteriaLoading ? (
                    <>
                      <Loader2 className="animate-spin" />
                      Finding systems…
                    </>
                  ) : (
                    <>
                      <Sparkles />
                      Get recommendations
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        <section className="space-y-6">
          {isCriteriaMode && (
            <>
              <div className="flex items-end justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold">Recommended systems</h2>
                  <p className="text-sm text-muted-foreground">
                    Scroll to load more — {PAGE_SIZE} systems per batch.
                  </p>
                </div>
                {criteriaMeta && (
                  <p className="text-sm text-muted-foreground">
                    Showing {recommendations.length} of {criteriaTotal}
                  </p>
                )}
              </div>

              <Separator />

              {isCriteriaError && (
                <Alert variant="destructive">
                  <AlertTitle>Could not load recommendations</AlertTitle>
                  <AlertDescription>
                    {criteriaError instanceof Error ? criteriaError.message : "Unknown error"}
                  </AlertDescription>
                </Alert>
              )}

              {isInitialCriteriaLoading && (
                <div className="space-y-4">
                  {[1, 2, 3].map((item) => (
                    <Card key={item}>
                      <CardContent className="space-y-3 pt-6">
                        <Skeleton className="h-5 w-1/3" />
                        <Skeleton className="h-4 w-2/3" />
                        <Skeleton className="h-24 w-full" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}

              {!isInitialCriteriaLoading && recommendations.length === 0 && !isCriteriaError && (
                <Alert>
                  <AlertTitle>No matches found</AlertTitle>
                  <AlertDescription>
                    Try relaxing filters such as minimum SEER, configuration, or system type.
                  </AlertDescription>
                </Alert>
              )}

              <div className="space-y-4">
                {recommendations.map((recommendation, index) => (
                  <SystemCard
                    key={recommendation.system.id}
                    recommendation={recommendation}
                    rank={index + 1}
                    onClick={() => setSelected({ recommendation, rank: index + 1 })}
                  />
                ))}
              </div>

              {recommendations.length > 0 && (
                <div ref={loadMoreRef} className="flex justify-center py-4">
                  {isFetchingNextCriteriaPage ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="size-4 animate-spin" />
                      Loading more…
                    </div>
                  ) : hasNextCriteriaPage ? (
                    <Button type="button" variant="outline" onClick={() => fetchNextCriteriaPage()}>
                      Load {PAGE_SIZE} more
                    </Button>
                  ) : (
                    <p className="text-sm text-muted-foreground">All results loaded</p>
                  )}
                </div>
              )}
            </>
          )}

          {isProductMode && (
            <>
              <div className="flex items-end justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold">Product search results</h2>
                  <p className="text-sm text-muted-foreground">
                    {matchedModel ? (
                      <>
                        Matched {componentTypeLabel(matchedType)}{" "}
                        <span className="font-mono font-medium text-foreground">{matchedModel}</span>
                      </>
                    ) : (
                      <>Searching for model "{productFirstPage?.query ?? productForm.model}"</>
                    )}
                  </p>
                </div>
                {productMeta && (
                  <p className="text-sm text-muted-foreground">
                    {productTotal} certified matchup{productTotal === 1 ? "" : "s"}
                  </p>
                )}
              </div>

              <Separator />

              {isProductError && (
                <Alert variant="destructive">
                  <AlertTitle>Could not search products</AlertTitle>
                  <AlertDescription>
                    {productError instanceof Error ? productError.message : "Unknown error"}
                  </AlertDescription>
                </Alert>
              )}

              {isInitialProductLoading && (
                <div className="space-y-4">
                  {[1, 2].map((item) => (
                    <Card key={item}>
                      <CardContent className="space-y-3 pt-6">
                        <Skeleton className="h-5 w-1/3" />
                        <Skeleton className="h-4 w-2/3" />
                        <Skeleton className="h-24 w-full" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}

              {!isInitialProductLoading && productMatchups.length === 0 && !isProductError && (
                <Alert>
                  <AlertTitle>No matchups found</AlertTitle>
                  <AlertDescription>
                    Check the model number spelling or try auto-detect instead of a specific
                    component type.
                  </AlertDescription>
                </Alert>
              )}

              {!isInitialProductLoading && boughtTogether.length > 0 && (
                <BoughtTogetherSection items={boughtTogether} searchedType={matchedType} />
              )}

              {!isInitialProductLoading && productMatchups.length > 0 && (
                <>
                  <div>
                    <h3 className="text-lg font-semibold">Similar matchups</h3>
                    <p className="text-sm text-muted-foreground">
                      Full AHRI-certified systems that include your searched component
                    </p>
                  </div>

                  <div className="space-y-4">
                    {productMatchups.map((recommendation, index) => (
                      <SystemCard
                        key={recommendation.system.id}
                        recommendation={recommendation}
                        rank={index + 1}
                        onClick={() => setSelected({ recommendation, rank: index + 1 })}
                      />
                    ))}
                  </div>

                  <div ref={productLoadMoreRef} className="flex justify-center py-4">
                    {isFetchingNextProductPage ? (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="size-4 animate-spin" />
                        Loading more…
                      </div>
                    ) : hasNextProductPage ? (
                      <Button type="button" variant="outline" onClick={() => fetchNextProductPage()}>
                        Load {PAGE_SIZE} more
                      </Button>
                    ) : (
                      <p className="text-sm text-muted-foreground">All matchups loaded</p>
                    )}
                  </div>
                </>
              )}
            </>
          )}

          {!hasSearched && (
            <Card className="border-dashed">
              <CardContent className="flex min-h-48 flex-col items-center justify-center gap-2 py-10 text-center">
                <Sparkles className="size-8 text-muted-foreground" />
                <p className="font-medium">No search yet</p>
                <p className="max-w-md text-sm text-muted-foreground">
                  Use system criteria to find bundles by tonnage and SEER, or search by outdoor,
                  coil, or furnace model number to see certified matchups and compatible parts.
                </p>
              </CardContent>
            </Card>
          )}

          <SystemDetailModal
            open={selected != null}
            recommendation={selected?.recommendation ?? null}
            rank={selected?.rank ?? 0}
            onClose={() => setSelected(null)}
          />
        </section>
      </main>
    </div>
  )
}
