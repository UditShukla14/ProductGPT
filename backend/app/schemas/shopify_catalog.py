from pydantic import BaseModel, Field

from app.schemas.component_search import ComponentSearchResponse


class ShopifyVariantSummary(BaseModel):
    id: str | None = None
    sku: str | None = None
    title: str | None = None
    price: str | None = None
    inventory_quantity: int | None = None
    available_for_sale: bool | None = None


class ShopifyProductSummary(BaseModel):
    id: str
    title: str
    vendor: str | None = None
    product_type: str | None = None
    sku: str | None = None
    price: str | None = None
    image_url: str | None = None
    status: str | None = None
    handle: str | None = None


class ShopifyProductDetail(ShopifyProductSummary):
    shopify_gid: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    inventory_quantity: int | None = None
    available_for_sale: bool | None = None
    variants: list[ShopifyVariantSummary] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class ShopifyProductSearchResponse(BaseModel):
    query: str
    results: list[ShopifyProductSummary]


class ShopifyProductRecommendation(BaseModel):
    product: ShopifyProductSummary
    order_count: int | None = None
    reason: str | None = None


class ShopifyProductRecommendationsResponse(BaseModel):
    product_id: str
    items: list[ShopifyProductRecommendation]


class ShopifyCategoryBrandGroup(BaseModel):
    vendor: str
    products: list[ShopifyProductSummary]


class ShopifySameCategoryByBrandResponse(BaseModel):
    product_id: str
    category: str | None = None
    current_vendor: str | None = None
    match_keywords: list[str] = Field(default_factory=list)
    brands: list[ShopifyCategoryBrandGroup] = Field(default_factory=list)


class ShopifyPublicProductResponse(BaseModel):
    """Combined public response: product detail + people-also-bought + other-options + AHRI matchups."""

    product_id: str
    product: ShopifyProductDetail
    bought_together: list[ShopifyProductRecommendation] = Field(default_factory=list)
    other_options: ShopifySameCategoryByBrandResponse
    matchups: ComponentSearchResponse
