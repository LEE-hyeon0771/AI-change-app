from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError
from pydantic import computed_field
from pydantic import field_validator
from dotenv import load_dotenv
import os

# .env 파일 자동 로드 (프로젝트 루트에 .env 가 있다고 가정)
load_dotenv()


class Settings(BaseModel):
    """Application configuration."""

    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    data_dir: Path = Field(default_factory=lambda: Path("data"))
    faiss_index_dir: Path = Field(default_factory=lambda: Path("data") / "faiss_index")

    allowed_lang_codes: tuple[Literal["ko", "en", "zh", "ja", "th"], ...] = (
        "ko",
        "en",
        "zh",
        "ja",
        "th",
    )

    @field_validator("openai_api_key")
    @classmethod
    def _check_api_key(cls, v: str) -> str:
        # 빈 값이면 실행 시점에 FastAPI에서 에러로 처리할 예정이라 여기선 그대로 둔다.
        return v or ""

    @computed_field
    @property
    def data_dir_path(self) -> Path:  # type: ignore[override]
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir

    @computed_field
    @property
    def faiss_index_dir_path(self) -> Path:  # type: ignore[override]
        self.faiss_index_dir.mkdir(parents=True, exist_ok=True)
        return self.faiss_index_dir


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        # FastAPI 시작 시점에 바로 에러를 보고 싶기 때문에 예외를 그대로 올린다.
        raise e


settings = get_settings()


