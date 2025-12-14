from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4

import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from ..core.config import settings
from ..core.models import DesignChangeInput, DesignChangeRecord


_VECTORSTORE: FAISS | None = None
_LATEST_CHANGE: DesignChangeRecord | None = None


def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        api_key=settings.openai_api_key,
        model=settings.openai_embedding_model,
    )


def _build_text(change: DesignChangeRecord) -> str:
    return (
        f"[설계변경 ID: {change.id}]\n"
        f"변경일: {change.change_date.isoformat()}\n"
        f"제목: {change.title}\n"
        f"기관명: {change.organization or '미상'}\n"
        f"사업명: {change.project_name or '미상'}\n"
        f"요청 발주처: {change.client or '미상'}\n"
        f"작성자: {change.author or '미상'}\n"
        f"내용:\n{change.description}"
    )


def _metadata(change: DesignChangeRecord) -> dict:
    return {
        "id": change.id,
        "change_date": change.change_date.isoformat(),
        "title": change.title,
        "author": change.author,
        "organization": change.organization,
        "project_name": change.project_name,
        "client": change.client,
        "created_at": change.created_at.isoformat(),
    }


def _vectorstore_path() -> Tuple[Path, Path]:
    index_dir = settings.faiss_index_dir_path
    index_file = index_dir / "index.faiss"
    store_file = index_dir / "index.pkl"
    return index_file, store_file


def _create_empty_vectorstore() -> FAISS:
    """문서가 하나도 없을 때 사용할 빈 FAISS 인덱스 생성."""
    embedding = _get_embeddings()
    # 간단한 문장 하나를 임베딩해서 차원을 구한다.
    dim = len(embedding.embed_query("init"))
    index = faiss.IndexFlatL2(dim)
    docstore = InMemoryDocstore({})
    index_to_docstore_id: dict[int, str] = {}
    return FAISS(
        embedding_function=embedding,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id,
    )


def load_vectorstore() -> FAISS:
    """기존 FAISS 인덱스를 로드하거나, 없으면 새로 생성."""
    global _VECTORSTORE
    if _VECTORSTORE is not None:
        return _VECTORSTORE

    index_dir = settings.faiss_index_dir_path
    index_file, store_file = _vectorstore_path()

    if index_file.exists() and store_file.exists():
        _VECTORSTORE = FAISS.load_local(
            str(index_dir),
            _get_embeddings(),
            allow_dangerous_deserialization=True,
        )
    else:
        # 문서가 하나도 없는 초기 상태용 빈 인덱스 생성
        _VECTORSTORE = _create_empty_vectorstore()
        _VECTORSTORE.save_local(str(index_dir))

    return _VECTORSTORE


def save_vectorstore() -> None:
    vs = load_vectorstore()
    vs.save_local(str(settings.faiss_index_dir_path))


def add_design_change(change_input: DesignChangeInput) -> DesignChangeRecord:
    """설계 변경 사항을 벡터DB에 추가하고, 로컬 메타데이터도 저장."""
    global _LATEST_CHANGE

    vs = load_vectorstore()

    record = DesignChangeRecord(
        id=uuid4().hex,
        change_date=change_input.change_date,
        title=change_input.title,
        description=change_input.description,
        author=change_input.author,
        organization=change_input.organization,
        project_name=change_input.project_name,
        client=change_input.client,
        created_at=datetime.utcnow(),
    )

    doc = Document(
        page_content=_build_text(record),
        metadata=_metadata(record),
    )
    vs.add_documents([doc])
    save_vectorstore()

    _LATEST_CHANGE = record
    _append_change_log(record)

    return record


def get_latest_change() -> DesignChangeRecord | None:
    global _LATEST_CHANGE
    if _LATEST_CHANGE is not None:
        return _LATEST_CHANGE

    # 서버 재시작 시에는 change_log.json 에서 마지막 레코드를 읽어온다.
    log_path = settings.data_dir_path / "change_log.jsonl"
    if not log_path.exists():
        return None

    last_line = None
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last_line = line

    if not last_line:
        return None

    try:
        obj = json.loads(last_line)
        from datetime import datetime as _dt

        _LATEST_CHANGE = DesignChangeRecord(
            id=obj["id"],
            change_date=_dt.fromisoformat(obj["change_date"]).date(),
            title=obj["title"],
            description=obj["description"],
            author=obj.get("author"),
            organization=obj.get("organization"),
            project_name=obj.get("project_name"),
            client=obj.get("client"),
            created_at=_dt.fromisoformat(obj["created_at"]),
        )
        return _LATEST_CHANGE
    except Exception:
        return None


def _append_change_log(record: DesignChangeRecord) -> None:
    log_path = settings.data_dir_path / "change_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "id": record.id,
        "change_date": record.change_date.isoformat(),
        "title": record.title,
        "description": record.description,
        "author": record.author,
        "organization": record.organization,
        "project_name": record.project_name,
        "client": record.client,
        "created_at": record.created_at.isoformat(),
    }

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def get_retriever():
    vs = load_vectorstore()
    return vs.as_retriever(search_kwargs={"k": 5})


def list_all_changes_from_log() -> List[DesignChangeRecord]:
    """디버깅/관리용: change_log.jsonl 전체 읽기."""
    log_path = settings.data_dir_path / "change_log.jsonl"
    result: List[DesignChangeRecord] = []
    if not log_path.exists():
        return result

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                from datetime import datetime as _dt

                record = DesignChangeRecord(
                    id=obj["id"],
                    change_date=_dt.fromisoformat(obj["change_date"]).date(),
                    title=obj["title"],
                    description=obj["description"],
                    author=obj.get("author"),
                    organization=obj.get("organization"),
                    project_name=obj.get("project_name"),
                    client=obj.get("client"),
                    created_at=_dt.fromisoformat(obj["created_at"]),
                )
                result.append(record)
            except Exception:
                continue
    return result


