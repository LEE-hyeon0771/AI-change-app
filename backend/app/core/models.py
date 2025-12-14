from datetime import datetime, date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LanguageCode(str, Enum):
    ko = "ko"
    en = "en"
    zh = "zh"
    vi = "vi"
    uk = "uk"


class DesignChangeInput(BaseModel):
    """관리자가 입력하는 설계 변경 사항."""

    change_date: date = Field(description="설계 변경 일자")
    title: str = Field(description="변경 제목 또는 번호")
    description: str = Field(description="변경 상세 내용 (원문 어떤 언어든 가능)")
    author: Optional[str] = Field(default=None, description="등록자 (선택)")
    organization: Optional[str] = Field(
        default=None, description="기관명 (예: 발주기관/시행사 등, 선택)"
    )
    project_name: Optional[str] = Field(
        default=None, description="사업명 또는 프로젝트명 (선택)"
    )
    client: Optional[str] = Field(
        default=None, description="요청 발주처 / 의뢰 부서 등 (선택)"
    )


class DesignChangeRecord(DesignChangeInput):
    """저장용 설계 변경 레코드."""

    id: str = Field(description="고유 ID")
    created_at: datetime = Field(description="시스템에 저장된 시각")


class AdminChangeResponse(BaseModel):
    success: bool
    change: DesignChangeRecord


class LatestChangeSummary(BaseModel):
    id: str
    change_date: date
    title: str
    created_at: datetime
    organization: Optional[str] = None
    project_name: Optional[str] = None
    client: Optional[str] = None


class LatestChangeResponse(BaseModel):
    """작업자 페이지에서 폴링할 최신 변경 요약."""

    has_change: bool
    latest: Optional[LatestChangeSummary] = None


class LatestChangeTranslatedResponse(BaseModel):
    """언어별로 번역된 최신 변경 요약 (필드 단위)."""

    id: str
    language: LanguageCode
    organization: str
    project_name: str
    title: str
    client: str
    change_date: str


class ChatMessage(BaseModel):
    role: str
    content: str


class WorkerChatRequest(BaseModel):
    language: LanguageCode = Field(
        description="작업자가 선택한 언어 코드",
        examples=["ko", "en", "zh", "vi", "uk"],
    )
    question: str = Field(description="작업자가 물어보는 질문")
    worker_id: Optional[str] = Field(
        default=None, description="작업자 ID (로그/추적용, 선택)"
    )
    history: Optional[List[ChatMessage]] = Field(
        default=None, description="간단한 이전 대화 내역 (선택)"
    )


class WorkerChatAnswerSource(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    change_date: Optional[date] = None


class WorkerChatResponse(BaseModel):
    answer: str
    language: LanguageCode
    sources: List[WorkerChatAnswerSource] = Field(default_factory=list)


