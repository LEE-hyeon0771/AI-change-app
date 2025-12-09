from __future__ import annotations

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
)
from .vectorstore import get_retriever


LANGUAGE_NAME_MAP: Dict[LanguageCode, str] = {
    LanguageCode.ko: "Korean",
    LanguageCode.en: "English",
    LanguageCode.zh: "Chinese",
    LanguageCode.ja: "Japanese",
    LanguageCode.th: "Thai",
}


def _build_system_prompt() -> str:
    return (
        "You are an AI assistant that explains engineering design change notices to on-site workers.\n"
        "You MUST always answer in the target language specified by the user.\n"
        "Use the provided design change documents as the primary source of truth.\n"
        "If the question is unrelated to design changes, politely say you can only answer about design changes.\n"
        "Explain in a concise and practical way that workers can easily understand.\n"
        "Always include important dates, IDs, and what exactly changed in the design.\n"
        "When answering about a specific proposal or design change, FIRST show a short summary block "
        "with the key metadata (organization, project name, proposal name, proposal date, client / ordering party) "
        "in the target language, then give a more detailed explanation.\n"
    )


def _build_prompt() -> ChatPromptTemplate:
    system_prompt = _build_system_prompt()
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "system",
                "Target language: {language_name} (code: {language_code}). "
                "Answer ONLY in this language.",
            ),
            (
                "system",
                "Here are relevant design change documents:\n{context}",
            ),
            (
                "human",
                "Question from worker:\n{question}\n"
                "If there is any safety-related impact, highlight it clearly.",
            ),
        ]
    )


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_chat_model,
        temperature=0.2,
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


