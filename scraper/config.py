from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str                         # Supabase connection string
    telegram_bot_token: str
    environment: str = "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
