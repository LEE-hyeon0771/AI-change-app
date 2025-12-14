"""
기존 설계 변경 데이터를 한 번에 FAISS 벡터DB로 넣어두기 위한 스크립트.

예상 입력 형식 (JSON Lines, UTF-8):

data/initial_changes.jsonl
--------------------------
{"change_date": "2024-01-03", "title": "벽체 두께 변경", "description": "지하 2층 외벽 두께를 200mm -> 240mm로 변경", "author": "홍길동"}
{"change_date": "2024-01-10", "title": "슬래브 철근 보강", "description": "3층 슬래브 상부근 D13 @200 -> D16 @150", "author": "김철수"}

위와 같이 한 줄마다 하나의 JSON 객체를 넣어두고, 아래 명령으로 실행합니다:

    cd backend
    python -m app.services.ingest_existing_data data/initial_changes.jsonl
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

from ..core.models import DesignChangeInput
from .vectorstore import add_design_change


def _load_jsonl(path: Path) -> Iterable[dict]:
  with path.open("r", encoding="utf-8") as f:
      for line in f:
          line = line.strip()
          if not line:
              continue
          try:
              yield json.loads(line)
          except json.JSONDecodeError:
              print(f"[WARN] JSON 파싱 실패, 건너뜀: {line[:80]}...")


def ingest_jsonl(path: Path) -> None:
    if not path.exists():
        print(f"[ERROR] 파일을 찾을 수 없습니다: {path}")
        return

    count_ok = 0
    count_fail = 0

    for obj in _load_jsonl(path):
        try:
            # 최소 필드: change_date, title, description
            raw_date = obj.get("change_date")
            if not raw_date:
                raise ValueError("change_date 가 없습니다.")

            change = DesignChangeInput(
                change_date=date.fromisoformat(str(raw_date)),
                title=str(obj.get("title") or ""),
                description=str(obj.get("description") or ""),
                author=obj.get("author"),
                organization=obj.get("organization"),
                project_name=obj.get("project_name"),
                client=obj.get("client"),
            )
            add_design_change(change)
            count_ok += 1
        except Exception as e:
            print(f"[WARN] 레코드 변환/저장 실패: {e} / 데이터: {obj}")
            count_fail += 1

    print(f"[DONE] 총 {count_ok}건 성공, {count_fail}건 실패")


def main(argv: list[str] | None = None) -> None:
    argv = argv or sys.argv[1:]
    if not argv:
        print("사용법: python -m app.services.ingest_existing_data <jsonl_파일경로>")
        sys.exit(1)

    file_path = Path(argv[0])
    ingest_jsonl(file_path)


if __name__ == "__main__":
    main()


