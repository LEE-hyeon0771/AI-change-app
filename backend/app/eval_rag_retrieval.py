"""
RAG retrieval 평가 스크립트.

역할
-----
- 미리 준비한 테스트셋 JSON(`rag_testset.json`)을 읽어서
  - 각 케이스에 대해 `/worker/chat` 호출
  - 반환된 `sources` 의 문서 ID와 정답(`gold_doc_ids`)을 비교
- hit@k / precision@k / recall@k 와
  - negative / oos 케이스에 대한 hallucination rate 를 계산
- 사람 눈으로 확인하기 좋은 TXT 리포트를 생성한다.

실행 예시 (Windows PowerShell)
-----
cd D:\\AI-change-app
.\.venv\Scripts\Activate.ps1
cd backend
python -m app.eval_rag_retrieval

테스트셋 JSON 예시 스키마 (리스트 형태)
-----
[
  {
    "id": "case_ko_01",
    "language": "ko",
    "question": "성남복정1 C3BL 설계 변경 내용과 LCC 절감 효과를 알려줘.",
    "gold_doc_ids": ["09715d1100d84681b14a3aa90ce4586d"],
    "type": "positive"   // optional: "positive" | "multi" | "negative" | "oos"
  },
  {
    "id": "case_neg_01",
    "language": "ko",
    "question": "존재하지 않는 기관/사업/제안 조합에 대한 설계변경을 알려줘.",
    "gold_doc_ids": [],
    "type": "negative"
  }
]
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

import requests


API_BASE_URL = os.getenv("WORKER_API_BASE", "http://localhost:8000")
TESTSET_PATH = os.getenv("RAG_TESTSET_PATH", "rag_testset.json")
OUTPUT_PATH = os.getenv("RAG_RETRIEVAL_OUTPUT_PATH", "rag_eval_retrieval.txt")
TOP_K = int(os.getenv("RAG_TOP_K", "5"))


def load_test_cases(path: str) -> List[Dict[str, Any]]:
    """테스트셋 JSON 로드."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("rag_testset.json 최상위는 리스트여야 합니다.")
    return data


def call_worker_chat(language: str, question: str) -> Dict[str, Any]:
    """백엔드 `/worker/chat` 호출."""
    url = f"{API_BASE_URL}/worker/chat"
    payload = {
        "language": language,
        "question": question,
        "history": [],
    }
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def compute_retrieval_metrics(
    gold_ids: List[str], returned_ids: List[str], k: int
) -> Tuple[int, float, float]:
    """
    hit@k, precision@k, recall@k 계산.

    - hit@k : 정답 집합과 top-k 예측 집합이 겹치면 1, 아니면 0
    - precision@k : |gold ∩ pred_top_k| / |pred_top_k|
    - recall@k : |gold ∩ pred_top_k| / |gold|
    """
    gold_set = set(gold_ids)
    pred_top_k = returned_ids[:k]
    pred_set = set(pred_top_k)

    if not pred_top_k:
        hit = 0
        precision = 0.0
    else:
        inter = gold_set & pred_set
        hit = 1 if inter else 0
        precision = len(inter) / len(pred_top_k)

    if not gold_set:
        recall = 0.0
    else:
        inter = gold_set & pred_set
        recall = len(inter) / len(gold_set)

    return hit, precision, recall


def format_case_block(row: Dict[str, Any]) -> str:
    """각 테스트 케이스 결과를 텍스트 블록으로 변환."""
    lines: List[str] = []
    lines.append(f"=== Case: {row['case_id']} (language={row['language']}, type={row['type']}) ===")
    lines.append("")
    lines.append("[Question]")
    lines.append(row["question"])
    lines.append("")
    lines.append("[Gold doc IDs]")
    lines.append(", ".join(row.get("gold_doc_ids", [])) or "(none)")
    lines.append("")
    lines.append("[Returned doc IDs (top_k)]")
    lines.append(", ".join(row.get("returned_ids", [])) or "(none)")
    lines.append("")
    lines.append("[Metrics]")
    lines.append(f"- hit@{TOP_K}      : {row.get('hit_at_k', '-')}")
    lines.append(f"- precision@{TOP_K}: {row.get('precision_at_k', '-')}")
    lines.append(f"- recall@{TOP_K}   : {row.get('recall_at_k', '-')}")
    if row.get("hallucination") is not None:
        lines.append(f"- hallucination    : {row['hallucination']}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    print(f"[RAG EVAL] Loading test cases from {TESTSET_PATH}")
    cases = load_test_cases(TESTSET_PATH)

    pos_hit_sum = 0
    pos_prec_sum = 0.0
    pos_rec_sum = 0.0
    pos_cnt = 0

    neg_cnt = 0
    neg_hallu_cnt = 0

    rows: List[Dict[str, Any]] = []

    for case in cases:
        case_id = case.get("id", "unknown")
        language = case.get("language", "ko")
        question = case.get("question", "")
        gold_doc_ids: List[str] = case.get("gold_doc_ids", []) or []
        case_type = case.get("type", "positive")

        print(f"=== Running case {case_id} (lang={language}, type={case_type}) ===")

        chat_resp = call_worker_chat(language, question)
        sources = chat_resp.get("sources", [])
        returned_ids = [str(s.get("id", "")) for s in sources if s.get("id")]

        row: Dict[str, Any] = {
            "case_id": case_id,
            "language": language,
            "type": case_type,
            "question": question,
            "gold_doc_ids": gold_doc_ids,
            "returned_ids": returned_ids[:TOP_K],
        }

        # positive / multi 케이스: retrieval 성능 계산
        if gold_doc_ids:
            hit, prec, rec = compute_retrieval_metrics(gold_doc_ids, returned_ids, TOP_K)
            row["hit_at_k"] = hit
            row["precision_at_k"] = round(prec, 3)
            row["recall_at_k"] = round(rec, 3)

            pos_hit_sum += hit
            pos_prec_sum += prec
            pos_rec_sum += rec
            pos_cnt += 1

            row["hallucination"] = None
        else:
            # negative / oos 케이스: hallucination 여부만 체크
            neg_cnt += 1
            hallucination = 1 if returned_ids else 0
            neg_hallu_cnt += hallucination
            row["hit_at_k"] = "-"
            row["precision_at_k"] = "-"
            row["recall_at_k"] = "-"
            row["hallucination"] = hallucination

        rows.append(row)

    # 요약 통계 계산
    summary_lines: List[str] = []
    summary_lines.append("=== SUMMARY ===")
    summary_lines.append(f"- total cases           : {len(cases)}")
    summary_lines.append(f"- positive/multi cases  : {pos_cnt}")
    summary_lines.append(f"- negative/oos cases    : {neg_cnt}")
    summary_lines.append("")

    if pos_cnt > 0:
        avg_hit = pos_hit_sum / pos_cnt
        avg_prec = pos_prec_sum / pos_cnt
        avg_rec = pos_rec_sum / pos_cnt
        summary_lines.append(f"- avg hit@{TOP_K}       : {avg_hit:.3f}")
        summary_lines.append(f"- avg precision@{TOP_K} : {avg_prec:.3f}")
        summary_lines.append(f"- avg recall@{TOP_K}    : {avg_rec:.3f}")
    else:
        summary_lines.append(f"- avg hit@{TOP_K}       : N/A")
        summary_lines.append(f"- avg precision@{TOP_K} : N/A")
        summary_lines.append(f"- avg recall@{TOP_K}    : N/A")

    if neg_cnt > 0:
        hallu_rate = neg_hallu_cnt / neg_cnt
        summary_lines.append(f"- hallucination rate    : {hallu_rate:.3f}  (negative/oos cases)")
    else:
        summary_lines.append(f"- hallucination rate    : N/A")

    summary_lines.append("")

    # TXT 리포트 작성
    blocks = [format_case_block(r) for r in rows]
    report = "\n".join(blocks) + "\n" + "\n".join(summary_lines)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n[RAG EVAL] Saved retrieval report to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()


