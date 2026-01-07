from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "local"

    # ✅ NEW: allow full URL override
    database_url_override: str | None = None

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "sentinelops"
    db_user: str = "postgres"
    db_password: str = ""

    stripe_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        # 1) Prefer explicit DATABASE_URL
        if self.database_url_override:
            return self.database_url_override

        # 2) Fallback to postgres assembled URL
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?connect_timeout=3"
        )


settings = Settings()
