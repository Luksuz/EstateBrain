from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Supabase
    supabase_url: str = "https://erjkgyvfzkxugiwcnwxb.supabase.co"
    supabase_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyamtneXZmemt4dWdpd2Nud3hiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NDMzNjczNSwiZXhwIjoyMDc5OTEyNzM1fQ.MO6zd64btqxpgx9wc6lK4KqVqQpaO4Nf2vKEYW9W7hs"  # Service role key for backend operations
    supabase_anon_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyamtneXZmemt4dWdpd2Nud3hiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQzMzY3MzUsImV4cCI6MjA3OTkxMjczNX0.WYLxy5Vcv6dZ4DZZiser2pi_6AbTbB5tO6RfJMkHUVc"
    
    # Firecrawl
    firecrawl_api_key: str = "fc-ebd51da511df49be9f7d515ac9bc130b"
    firecrawl_api_url: str = "https://api.firecrawl.dev/v2/scrape"
    
    # OpenRouter (LLM)
    openrouter_api_key: str = "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"
    openrouter_model_name: str = "google/gemini-3-pro-preview"
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars like OPENAI_API_KEY


@lru_cache
def get_settings() -> Settings:
    return Settings()

