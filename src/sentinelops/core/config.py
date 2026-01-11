from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "local"

    # ✅ NEW: allow full URL override
    database_url_override: str | None = None

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "sentinelops"
    db_user: str = "postgres"
    db_password: str | None = None

    stripe_api_key: str | None = None
    stripe_webhook_secret: str | None = None

    slack_webhook_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        # 1) Prefer explicit DATABASE_URL
        if self.database_url_override:
            return self.database_url_override
        
        password = self.db_password or ""
        auth = f"{self.db_user}:{password}" if password else self.db_user

        # 2) Fallback to postgres assembled URL
        return (
            f"postgresql+psycopg://{auth}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?connect_timeout=3"
        )


settings = Settings()
