from 	pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_url: str = "http://localhost"  # Added default value
    pocketbase_url: str = "http://localhost:8090"  # Added default value
    redis_url: str = "" # Keep as required
    allow_plugins: bool = False

    class Config:
        env_file = ".env"


settings = Settings()