from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    use_llm: bool = os.getenv("USE_LLM", "false").lower() == "true"
    enable_kg: bool = os.getenv("ENABLE_KG", "true").lower() == "true"
    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "")
    sarvam_base_url: str = os.getenv(
        "SARVAM_BASE_URL", "https://api.sarvam.ai/v1/chat/completions"
    )
    sarvam_model: str = os.getenv("SARVAM_MODEL", "sarvam-30b")
    catalog_path: Path = Path(os.getenv("CATALOG_PATH", "data/shl_catalog.json"))
    top_k_retrieval: int = int(os.getenv("TOP_K_RETRIEVAL", "30"))
    top_k_final: int = min(10, int(os.getenv("TOP_K_FINAL", "10")))


@lru_cache
def get_settings() -> Settings:
    return Settings()
