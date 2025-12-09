from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .services.agent import worker_chat
from .core.config import settings
from .core.models import (
    AdminChangeResponse,
    DesignChangeInput,
    LatestChangeResponse,
    LatestChangeSummary,
    WorkerChatRequest,
    WorkerChatResponse,
)
from .services.vectorstore import add_design_change, get_latest_change, load_vectorstore

app = FastAPI(
    title="AI Design Change App",
    description="관리자/노동자용 설계변경 챗봇 백엔드 (FastAPI + LangChain + OpenAI + FAISS)",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 단계에서는 전체 허용, 운영 시 도메인 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    # 설정 및 벡터스토어를 미리 초기화
    if not settings.openai_api_key:
        # 실행은 되지만, 실제 호출 시 에러가 나도록 둔다.
        print("[WARN] OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    load_vectorstore()
    print("[INFO] FAISS vector store loaded or initialized.")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "openai_configured": bool(settings.openai_api_key),
    }


@app.post("/admin/changes", response_model=AdminChangeResponse, tags=["admin"])
def create_design_change(change: DesignChangeInput) -> AdminChangeResponse:
    """
    관리자 페이지에서 설계 변경 사항을 등록하는 엔드포인트.
    - 입력: 날짜, 제목, 내용, 작성자(선택)
    - 처리: 임베딩 생성 후 FAISS 벡터DB에 누적 저장
    - 출력: 저장된 레코드 정보
    """
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured.")

    try:
        record = add_design_change(change)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add design change: {e}")

    return AdminChangeResponse(success=True, change=record)


@app.get("/worker/latest-change", response_model=LatestChangeResponse, tags=["worker"])
def get_latest_change_for_worker() -> LatestChangeResponse:
    """
    노동자 페이지에서 폴링해서 확인할 수 있는 최신 설계 변경 요약.
    - Flutter 쪽에서는 마지막으로 본 id 를 로컬에 저장해 두었다가,
      여기서 받은 latest.id 와 다르면 '새로운 설계변경이 있습니다' 알림을 띄우면 됨.
    """
    record = get_latest_change()
    if record is None:
        return LatestChangeResponse(has_change=False, latest=None)

    summary = LatestChangeSummary(
        id=record.id,
        change_date=record.change_date,
        title=record.title,
        created_at=record.created_at,
        organization=record.organization,
        project_name=record.project_name,
        client=record.client,
    )
    return LatestChangeResponse(has_change=True, latest=summary)


@app.post("/worker/chat", response_model=WorkerChatResponse, tags=["worker"])
def worker_chat_endpoint(req: WorkerChatRequest) -> WorkerChatResponse:
    """
    노동자 페이지에서 사용하는 챗봇 엔드포인트.
    - language: 노동자가 선택한 언어 (ko, en, zh, ja, th)
    - question: 질문 내용
    - history: (선택) 이전 대화 내역
    """
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured.")

    try:
        return worker_chat(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")



