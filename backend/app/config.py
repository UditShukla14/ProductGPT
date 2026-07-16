from pathlib import Path
from typing import Annotated, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            PROJECT_ROOT / ".env",
            BACKEND_ROOT / ".env",
            ".env",
        ),
        env_file_encoding="utf-8",
    )

    project_root: Path = PROJECT_ROOT
    app_name: str = "ProductGPT"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'productgpt.db'}"
    default_goodman_ratings_xlsx: Path = (
        PROJECT_ROOT / "data" / "Goodman November Ratings_cleaned.xlsx"
    )
    default_r32_engineering_xlsx: Path = PROJECT_ROOT / "data" / "R32_Engineering_file.xlsx"
    default_od_sales_xlsx: Path = PROJECT_ROOT / "data" / "OD Sales 2025.xlsx"
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "productgpt"
    neo4j_database: str = "neo4j"
    neo4j_enabled: bool = True

    public_api_token: str = ""

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"
    anthropic_max_tokens: int = 1024

    shopify_api_base_url: str = ""
    shopify_api_token: str = ""
    shopify_api_shop_domain: str = ""
    shopify_api_page_limit: int = 0  # 0 = omit ?limit= (Worxstream default 20; sending limit causes 502)
    shopify_api_requests_per_minute: int = 100
    shopify_api_timeout_seconds: float = 60.0
    shopify_data_dir: Path = PROJECT_ROOT / "data" / "shopify"
    shopify_neo4j_database: str = "neo4j"
    shopify_sync_on_startup: bool = False
    shopify_enrich_details: bool = True
    shopify_enrich_detail_resources: Annotated[list[str], NoDecode] = [
        "products",
        "customers",
        "orders",
    ]

    @field_validator("shopify_enrich_detail_resources", mode="before")
    @classmethod
    def parse_shopify_enrich_detail_resources(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


settings = Settings()
