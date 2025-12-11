from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..core.config import settings
from ..core.models import (
    LanguageCode,
    WorkerChatRequest,
    WorkerChatResponse,
    WorkerChatAnswerSource,
    DesignChangeRecord,
)
from .vectorstore import get_retriever


BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")


LANGUAGE_NAME_MAP: Dict[LanguageCode, str] = {
    LanguageCode.ko: "Korean",
    LanguageCode.en: "English",
    LanguageCode.zh: "Chinese",
    LanguageCode.vi: "Vietnamese",
    LanguageCode.uk: "Ukrainian",
}


def _build_system_prompt() -> str:
    return _load_prompt("worker_system.txt")


def _build_prompt() -> ChatPromptTemplate:
    system_prompt = _build_system_prompt()
    language_prompt = _load_prompt("worker_language.txt")
    context_prompt = _load_prompt("worker_context.txt")
    human_prompt = _load_prompt("worker_human.txt")
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "system",
                language_prompt,
            ),
            (
                "system",
                context_prompt,
            ),
            (
                "human",
                human_prompt,
            ),
        ]
    )


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_chat_model,
        temperature=0.0,
    )


def _format_docs(docs: List[Document]) -> str:
    if not docs:
        return "No design change documents found."

    chunks = []
    for i, d in enumerate(docs, start=1):
        meta = d.metadata or {}
        chunks.append(
            f"[문서 {i}]\n"
            f"ID: {meta.get('id')}\n"
            f"제목(제안명): {meta.get('title')}\n"
            f"변경일(제안일자): {meta.get('change_date')}\n"
            f"기관명: {meta.get('organization')}\n"
            f"사업명: {meta.get('project_name')}\n"
            f"요청 발주처: {meta.get('client')}\n"
            f"내용 요약 후보:\n{d.page_content}\n"
        )
    return "\n\n".join(chunks)


def build_worker_chain():
    retriever = get_retriever()
    llm = _build_llm()
    prompt = _build_prompt()

    # LCEL 체인: 질문 -> 문서 검색 -> 프롬프트 -> LLM -> 문자열
    from langchain_core.runnables import RunnableParallel, RunnableMap

    def get_docs(inputs: dict) -> List[Document]:
        question: str = inputs["question"]
        return retriever.get_relevant_documents(question)

    chain_inputs = RunnableParallel(
        question=lambda x: x["question"],
        language_code=lambda x: x["language_code"],
        language_name=lambda x: x["language_name"],
        docs=get_docs,
    ) | RunnableMap(
        context=lambda x: _format_docs(x["docs"]),
        question=lambda x: x["question"],
        language_code=lambda x: x["language_code"],
        language_name=lambda x: x["language_name"],
        docs=lambda x: x["docs"],
    )

    chain = chain_inputs | prompt | llm | StrOutputParser()
    return chain


def worker_chat(req: WorkerChatRequest) -> WorkerChatResponse:
    chain = build_worker_chain()

    language_name = LANGUAGE_NAME_MAP[req.language]
    raw_answer = chain.invoke(
        {
            "question": req.question,
            "language_code": req.language.value,
            "language_name": language_name,
        }
    )

    # 검색된 문서에서 간단한 출처 정보만 다시 뽑기 위해 retriever 를 한 번 더 호출
    retriever = get_retriever()
    docs = retriever.get_relevant_documents(req.question)

    sources: List[WorkerChatAnswerSource] = []
    for d in docs:
        meta = d.metadata or {}
        sources.append(
            WorkerChatAnswerSource(
                id=meta.get("id"),
                title=meta.get("title"),
                change_date=None,
            )
        )

    return WorkerChatResponse(
        answer=raw_answer,
        language=req.language,
        sources=sources,
    )


def translate_latest_metadata_fields(
    record: DesignChangeRecord, language: LanguageCode
) -> dict[str, str]:
    """기관명/사업명/제안명/제안일자/요청 발주처를 선택 언어로 번역한 필드 딕셔너리."""
    # 한국어 탭이면 번역 필요 없음
    base_fields = {
        "organization": record.organization or "-",
        "project_name": record.project_name or "-",
        "title": record.title,
        "change_date": record.change_date.isoformat(),
        "client": record.client or "-",
    }

    if language == LanguageCode.ko:
        return base_fields

    llm = _build_llm()
    language_name = LANGUAGE_NAME_MAP[language]

    # 줄 단위로 번역: 파싱 오류를 없애기 위해 JSON 대신 라인 기반 프로토콜 사용
    phrases = "\n".join(
        [
            base_fields["organization"],
            base_fields["project_name"],
            base_fields["title"],
            base_fields["change_date"],
            base_fields["client"],
        ]
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You will receive EXACTLY 5 Korean phrases, one per line, "
                    "describing metadata of a design change.\n"
                    "Target language: {language_name} (code: {language_code}).\n"
                    "- Translate EACH line into the target language.\n"
                    "- Keep the order of lines exactly the same.\n"
                    "- Do NOT add numbers, bullets, labels, or extra commentary.\n"
                    "- The output MUST contain exactly 5 lines, each line only the translated phrase."
                ),
            ),
            ("human", "Korean phrases (one per line):\n{phrases}"),
        ]
    )

    chain = prompt | llm | StrOutputParser()

    try:
        raw = chain.invoke(
            {
                "language_name": language_name,
                "language_code": language.value,
                "phrases": phrases,
            }
        )
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        keys = ["organization", "project_name", "title", "change_date", "client"]
        result: dict[str, str] = {}
        for idx, key in enumerate(keys):
            if idx < len(lines):
                result[key] = lines[idx]
            else:
                result[key] = base_fields[key]
        return result
    except Exception:
        # 실패 시 원문 필드 사용
        return base_fields



