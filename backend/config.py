from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str                         # Supabase connection string
    secret_key: str                           # Session signing; generate with secrets.token_hex(32)
    telegram_bot_token: str
    github_dispatch_token: str                # Fine-grained PAT with workflow scope
    github_repo: str                          # e.g. "username/job-radar"
    environment: str = "production"
    session_max_age_seconds: int = 604800     # 7 days

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
