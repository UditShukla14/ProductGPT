from pathlib import Path
from typing import Annotated, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "ProductGPT"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'productgpt.db'}"
    default_goodman_ratings_xlsx: Path = (
        PROJECT_ROOT / "data" / "Goodman November Ratings_cleaned.xlsx"
    )
    default_shopify_products_csv: Path = PROJECT_ROOT / "data" / "products_export_1.csv"
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


settings = Settings()
