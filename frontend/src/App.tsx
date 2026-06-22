import { useEffect, useRef, useState } from "react"
import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Sparkles } from "lucide-react"

import { AppHeader } from "@/components/AppHeader"
import { BoughtTogetherMatchupsModal } from "@/components/BoughtTogetherMatchupsModal"
import { BoughtTogetherSection } from "@/components/BoughtTogetherSection"
import { CardCarousel } from "@/components/CardCarousel"
import { SearchSidebar, type SidebarSearchMode } from "@/components/SearchSidebar"
import { SystemCard } from "@/components/SystemCard"
import { SystemDetailModal } from "@/components/SystemDetailModal"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { DEFAULT_REFRIGERANT, componentTypeLabel } from "@/constants/hvac"
import { fetchComponentSearch, fetchRecommendations } from "@/lib/api"
import type {
  BoughtTogetherItem,
  ComponentSearchRequest,
  ComponentType,
  HvacRecommendation,
  HvacRecommendationRequest,
  HvacRecommendationResponse,
} from "@/types/api"

const PAGE_SIZE = 25

type SearchMode = "criteria" | "product"

type SearchForm = Omit<HvacRecommendationRequest, "limit" | "offset">

type ProductSearchForm = {
  model: string
  component_type: ComponentType
  equipment_category?: string
  refrigerant_type?: string
  flow?: string
  coil_width?: string
  furnace_width?: string
  prefer_higher_seer: boolean
}

const defaultForm: SearchForm = {
  tonnage: 2,
  min_seer: 15,
  equipment_category: "AC",
  refrigerant_type: DEFAULT_REFRIGERANT,
  prefer_higher_seer: true,
}

const defaultProductForm: ProductSearchForm = {
  model: "",
  component_type: "auto",
  refrigerant_type: DEFAULT_REFRIGERANT,
  prefer_higher_seer: true,
}

function buildSearchPayload(form: SearchForm): HvacRecommendationRequest {
  return {
    tonnage: form.tonnage || undefined,
    min_seer: form.min_seer || undefined,
    max_seer: form.max_seer || undefined,
    equipment_category: form.equipment_category || undefined,
    refrigerant_type: form.refrigerant_type || undefined,
    flow: form.flow || undefined,
    coil_width: form.coil_width || undefined,
    furnace_width: form.furnace_width || undefined,
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
  const queryClient = useQueryClient()
  const [sidebarMode, setSidebarMode] = useState<SidebarSearchMode>("criteria")
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
  const [criteriaExtra, setCriteriaExtra] = useState<HvacRecommendation[]>([])
  const [criteriaLoadMoreMeta, setCriteriaLoadMoreMeta] =
    useState<HvacRecommendationResponse["meta"] | null>(null)
  const [isLoadingMoreCriteria, setIsLoadingMoreCriteria] = useState(false)
  const activeSearchRef = useRef<HvacRecommendationRequest | null>(null)
  const activeProductSearchRef = useRef<ComponentSearchRequest | null>(null)

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

  const criteriaQuery = useQuery({
    queryKey: ["criteria-recommendations", searchKey],
    queryFn: () =>
      fetchRecommendations({
        ...activeSearchRef.current!,
        limit: PAGE_SIZE,
        offset: 0,
      }),
    enabled: activeMode === "criteria" && activeSearch !== null,
  })

  const {
    data: criteriaFirstPage,
    isFetching: isCriteriaFetching,
    isError: isCriteriaError,
    error: criteriaError,
  } = criteriaQuery

  async function loadMoreCriteria() {
    const paginationMeta = criteriaLoadMoreMeta ?? criteriaFirstPage?.meta
    if (isLoadingMoreCriteria || !paginationMeta?.has_more) return

    setIsLoadingMoreCriteria(true)
    try {
      const offset = (criteriaFirstPage?.recommendations.length ?? 0) + criteriaExtra.length
      const data = await fetchRecommendations({
        ...activeSearchRef.current!,
        limit: PAGE_SIZE,
        offset,
      })
      setCriteriaExtra((current) => [...current, ...data.recommendations])
      setCriteriaLoadMoreMeta(data.meta)
    } finally {
      setIsLoadingMoreCriteria(false)
    }
  }

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
    data: productData,
    isFetching: isProductFetching,
    isError: isProductError,
    error: productError,
    fetchNextPage: fetchNextProductPage,
    hasNextPage: hasNextProductPage,
    isFetchingNextPage: isFetchingNextProductPage,
  } = productQuery

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
    queryClient.removeQueries({ queryKey: ["recommendations"] })
    setCriteriaExtra([])
    setCriteriaLoadMoreMeta(null)
    setIsLoadingMoreCriteria(false)
    setActiveSearch(payload)
    setActiveMode("criteria")
    setSidebarMode("criteria")
    setSearchKey((key) => key + 1)
    setSelected(null)
  }

  function handleProductComponentTypeChange(value: ComponentType) {
    setProductForm((current) => ({
      ...current,
      component_type: value,
      coil_width: value === "coil" ? current.coil_width : undefined,
      furnace_width: value === "furnace" ? current.furnace_width : undefined,
    }))
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
      flow: productForm.flow,
      coil_width: productForm.component_type === "coil" ? productForm.coil_width : undefined,
      furnace_width:
        productForm.component_type === "furnace" ? productForm.furnace_width : undefined,
      prefer_higher_seer: productForm.prefer_higher_seer,
    }
    activeProductSearchRef.current = payload
    setActiveProductSearch(payload)
    setActiveMode("product")
    setSidebarMode("product")
    setProductSearchKey((key) => key + 1)
    setSelected(null)
    setPairedMatchupItem(null)
  }

  const recommendations: HvacRecommendation[] = [
    ...(criteriaFirstPage?.recommendations ?? []),
    ...criteriaExtra,
  ]
  const criteriaMeta = criteriaLoadMoreMeta ?? criteriaFirstPage?.meta
  const criteriaTotal = criteriaMeta?.total_ranked ?? 0
  const hasNextCriteriaPage = criteriaMeta?.has_more ?? false

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
    <div className="min-h-svh w-full max-w-[100vw] overflow-x-clip bg-background">
      <AppHeader />

      <main className="mx-auto w-full max-w-7xl min-w-0 px-4 py-4 sm:px-6 lg:flex lg:h-[calc(100dvh-var(--app-header-height,4rem))] lg:flex-col lg:overflow-hidden lg:py-4">
        <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[280px_minmax(0,1fr)] lg:items-start">
          <aside className="min-w-0 shrink-0 lg:sticky lg:top-0 lg:self-start lg:overflow-y-auto lg:overscroll-y-contain">
            <SearchSidebar
              sidebarMode={sidebarMode}
              onSidebarModeChange={setSidebarMode}
              criteriaForm={form}
              productForm={productForm}
              isCriteriaLoading={isInitialCriteriaLoading}
              isProductLoading={isInitialProductLoading}
              onCriteriaFieldChange={updateField}
              onProductFieldChange={updateProductField}
              onProductComponentTypeChange={handleProductComponentTypeChange}
              onCriteriaSubmit={handleCriteriaSubmit}
              onProductSubmit={handleProductSubmit}
            />
          </aside>

          <section className="min-h-0 min-w-0 space-y-4 overflow-y-auto overscroll-y-contain lg:max-h-full lg:pr-1">
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
                      <Skeleton key={item} className="h-[7.5rem] w-full rounded-xl" />
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
                  <div className="space-y-2">
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
                  <div className="flex justify-center py-2">
                    {isLoadingMoreCriteria ? (
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
                        onClick={() => void loadMoreCriteria()}
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
                      ? `${componentTypeLabel(matchedType, activeProductSearch?.equipment_category)} · ${matchedModel}`
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
                  <div className="flex w-full min-w-0 gap-3 overflow-hidden">
                    {[1, 2].map((item) => (
                      <Skeleton key={item} className="h-[7.5rem] w-full shrink-0 rounded-xl" />
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
                    <SectionHeading
                      title="Similar matchups"
                      count={
                        productMeta
                          ? `${productMatchups.length} / ${productTotal}`
                          : undefined
                      }
                    />

                    <CardCarousel ariaLabel="Similar matchups">
                      {productMatchups.map((recommendation, index) => (
                        <SystemCard
                          key={recommendation.system.id}
                          recommendation={recommendation}
                          rank={index + 1}
                          onClick={() => setSelected({ recommendation, rank: index + 1 })}
                        />
                      ))}
                    </CardCarousel>

                    <div className="flex justify-center py-2">
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
                    Use the sidebar to search by requirements or model number.
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
              flow={activeProductSearch?.flow}
              coilWidth={activeProductSearch?.coil_width}
              furnaceWidth={activeProductSearch?.furnace_width}
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
