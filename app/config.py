# app/config.py
# Loads settings from the .env file into one Python object called `settings`.

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings. Each field is filled from an environment variable or .env."""

    database_url: str                        # required: filled from DATABASE_URL
    base_url: str = "http://localhost:8000"  # optional: this default is used if BASE_URL is missing

    # required: filled from ADMIN_API_KEY. At least 32 characters, so an empty
    # or weak key (like the "change_me" placeholder) stops the app from starting.
    admin_api_key: str = Field(min_length=32)

    # Tell pydantic-settings to also read variables from the .env file.
    model_config = SettingsConfigDict(env_file=".env")


# Create ONE settings object when this file is first imported.
# Other files use it with: from app.config import settings
settings = Settings()
