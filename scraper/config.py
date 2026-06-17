from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str                         # Supabase connection string
    resend_api_key: str
    resend_from_email: str = "onboarding@resend.dev"
    environment: str = "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
