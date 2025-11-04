from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "fastapi-service"
    env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_name: str = "scrape-jobs"
    scraper_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    )
    scraper_timeout_seconds: float = 20.0
    scraper_retry_max_attempts: int = 3
    scraper_retry_intervals: tuple[int, ...] = (15, 30, 60)
    scraper_result_ttl_seconds: int = 3600
    scraper_failure_ttl_seconds: int = 3600
    scraper_raw_html_preview_limit: int = 4000
    database_url: str = "postgresql+psycopg://jobhub:jobhub@localhost:5432/jobhub"
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Pydantic v2 settings configuration. Ignore extra env keys like POSTGRES_*.
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
