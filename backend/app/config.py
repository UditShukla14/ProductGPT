from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "ProductGPT"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'productgpt.db'}"
    default_hvac_csv: Path = PROJECT_ROOT / "data" / "hvac_system_finder.csv"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
