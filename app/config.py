from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "dev-secret-key-change-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/saas_db"

    # JWT
    jwt_secret_key: str = "dev-jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_prefix: str = "saas"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    @property
    def kafka_topic_base(self) -> str:
        return f"{self.kafka_topic_prefix}.{self.app_env}"


settings = Settings()