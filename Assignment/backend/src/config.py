import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py path: Assignment/backend/src/config.py
# parents[3] points to the lecture01_ai_agent directory where .env lives.
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(ENV_PATH)

# Bridge assignment env naming to the standard Anthropic SDK variable.
if "CLAUDE_API_KEY" in os.environ:
    os.environ.setdefault("ANTHROPIC_API_KEY", os.environ["CLAUDE_API_KEY"])


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    anthropic_api_key: str = ""
    model_name: str = "claude-haiku-4-5"
    request_timeout_seconds: float = 10.0


settings = Settings()
