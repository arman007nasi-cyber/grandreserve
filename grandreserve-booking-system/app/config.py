from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Centralized application settings, loaded from environment variables (.env).
    Keeping every tunable in one place makes the security-sensitive values
    (JWT secret, token lifetimes) easy to audit and rotate.
    """

    database_url: str = "postgresql+asyncpg://booking_user:booking_pass@db:5432/booking_db"
    database_url_sync: str = "postgresql://booking_user:booking_pass@db:5432/booking_db"

    redis_url: str = "redis://redis:6379/0"

    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    support_email: str = "support-x7q2f9@grandreserve-demo.com"

    # How long a table stays "held" for a user while they finish checkout,
    # before the hold expires and the table becomes available again.
    reservation_hold_seconds: int = 120

    class Config:
        env_file = ".env"


settings = Settings()
