from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "fastapi-service"
    env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()