"""
LLM-as-judge 기반 RAG 평가 스크립트.

역할
-----
- FastAPI 백엔드의 `/worker/chat` 엔드포인트를 호출해서 실제 답변을 받고
- OpenAI Chat LLM을 "판사(judge)" 로 사용해
  - relevance / coverage / structure / language_quality
  - comment
  항목으로 질적 평가를 수행한 뒤
- 사람 눈으로 바로 볼 수 있도록 TXT 리포트를 생성한다.

실행 예시 (Windows PowerShell)
-----
cd D:\\AI-change-app
.\.venv\Scripts\Activate.ps1
cd backend
python -m app.eval_llm_judge
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_openai import ChatOpenAI
from app.core.config import settings


API_BASE_URL = os.getenv("WORKER_API_BASE", "http://localhost:8000")
EVAL_MODEL = os.getenv("EVAL_MODEL", "gpt-4.1-mini")
OUTPUT_PATH = os.getenv("EVAL_OUTPUT_PATH", "rag_eval_llm_judge.txt")


# 1) 평가 대상 테스트 케이스 정의
# 실제로 사용할 때는 이 리스트를 자유롭게 추가/수정하면 된다.
TEST_CASES: List[Dict[str, Any]] = [
    {
        "id": "ko_1",
        "language": "ko",
        "question": "성남복정1 C3BL 설계 변경 내용과 LCC 절감 효과를 알려줘.",
        "expected_key_points": [
            "성남복정1 C3BL",
            "LCC 절감 효과",
        ],
    },
    {
        "id": "ko_2",
        "language": "ko",
        "question": "가장 최근에 등록된 설계변경의 기관명, 사업명, 제안명, 제안일자를 알려줘.",
        "expected_key_points": [
            "가장 최근 설계변경",
            "기관명",
            "사업명",
            "제안명",
            "제안일자",
        ],
    },
    {
        "id": "zh_1",
        "language": "zh",
        "question": "请用中文说明最近的设计变更内容和节约成本效果。",
        "expected_key_points": [
            "最近 설계변경",
            "节约成本",
        ],
    },
    {
        "id": "en_1",
        "language": "en",
        "question": "In English, summarize the latest design change and its impact on life-cycle cost (LCC).",
        "expected_key_points": [
            "latest design change",
            "life-cycle cost",
        ],
    },
]


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


def build_judge_chain() -> Any:
    """LLM-as-judge 체인 구성."""
    # config 에서 불러온 키를 환경변수에 주입 (ChatOpenAI 가 OPENAI_API_KEY 를 참조)
    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

    llm = ChatOpenAI(model=EVAL_MODEL, temperature=0.0)

    system_prompt = """
You are an expert evaluator for a RAG-based design-change assistant
used on construction design-change (VE) data.

You will receive:
- The user's question
- The assistant's answer
- A list of key points that the answer should ideally cover
- The language code of the answer (ko, en, zh, vi, uk)

You must score the answer on these 4 dimensions, each as an integer 1–5:

1) relevance
   - 5: Directly and fully answers the user's question.
   - 3: Partially answers or includes some irrelevant content.
   - 1: Mostly off-topic or does not answer the question.

2) coverage
   - Consider the "expected key points" list.
   - Count a key point as "covered" if:
     - The answer explicitly mentions it, OR
     - The answer clearly states that the information is not available
       in the data (e.g., '미기재', 'Not specified', '정보가 제공되지 않음').
   - 5: Almost all key points are covered.
   - 3: About half of the key points are covered.
   - 1: Very few key points are covered.

3) structure
   - Target ideal structure:
     - At the top: a clear metadata summary block for the design change
       (e.g., organization, project name, proposal title, proposal date, client),
       presented in a compact list or table-like format.
     - Below that: one or more paragraphs explaining details (effects on LCC, etc.).
   - 5: The answer clearly follows this pattern
        (metadata summary block first, then explanation).
   - 3: Partially structured (some metadata and some explanation, but mixed together).
   - 1: No clear structure; hard to distinguish metadata from explanation.

4) language_quality
   - The answer should be natural, clear, and appropriate for the given language code.
   - 5: Fluent and natural; no major grammatical issues.
   - 3: Understandable but with some awkward phrasing.
   - 1: Difficult to understand or wrong language.

Return ONLY a valid JSON object with the following keys:
- "relevance": integer 1–5
- "coverage": integer 1–5
- "structure": integer 1–5
- "language_quality": integer 1–5
- "comment": a short explanation in Korean summarizing the main reasons for the scores

Do not include any extra keys, comments, or text outside the JSON object.
"""

    human_prompt = """
[Language]
{language}

[User question]
{question}

[Assistant answer]
{answer}

[Expected key points]
{expected_key_points}

Please rate this answer according to the instructions.
"""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt.strip()),
            ("human", human_prompt.strip()),
        ]
    )

    chain = prompt | llm | StrOutputParser()
    return chain


def format_case_block(row: Dict[str, Any]) -> str:
    """각 테스트 케이스 결과를 사람 눈으로 보기 좋은 텍스트 블록으로 변환."""
    lines: List[str] = []
    lines.append(f"=== Case: {row['case_id']} (language={row['language']}) ===")
    lines.append("")
    lines.append(f"[Question]")
    lines.append(row["question"])
    lines.append("")
    lines.append(f"[Answer]")
    lines.append(row["answer"])
    lines.append("")
    lines.append(f"[Sources]")
    lines.append(row.get("sources", ""))
    lines.append("")
    lines.append("[Scores]")
    lines.append(f"- relevance       : {row.get('relevance')}")
    lines.append(f"- coverage        : {row.get('coverage')}")
    lines.append(f"- structure       : {row.get('structure')}")
    lines.append(f"- language_quality: {row.get('language_quality')}")
    lines.append("")
    if row.get("comment"):
        lines.append("[Judge comment]")
        lines.append(row["comment"])
        lines.append("")
    lines.append("")  # extra newline between cases
    return "\n".join(lines)


def main() -> None:
    judge_chain = build_judge_chain()

    results: List[Dict[str, Any]] = []

    for case in TEST_CASES:
        print(f"=== Running case {case['id']} ({case['language']}) ===")
        chat_resp = call_worker_chat(case["language"], case["question"])
        answer = chat_resp.get("answer", "")
        sources = chat_resp.get("sources", [])

        # Judge 호출
        import json

        raw_judge = judge_chain.invoke(
            {
                "language": case["language"],
                "question": case["question"],
                "answer": answer,
                "expected_key_points": "\n".join(case["expected_key_points"]),
            }
        )

        try:
            judge = json.loads(raw_judge)
        except Exception:
            judge = {
                "relevance": None,
                "coverage": None,
                "structure": None,
                "language_quality": None,
                "comment": f"parse_error: {raw_judge[:200]}",
            }

        row: Dict[str, Any] = {
            "case_id": case["id"],
            "language": case["language"],
            "question": case["question"],
            "answer": answer,
            "sources": str(sources),
            "relevance": judge.get("relevance"),
            "coverage": judge.get("coverage"),
            "structure": judge.get("structure"),
            "language_quality": judge.get("language_quality"),
            "comment": judge.get("comment", ""),
        }
        results.append(row)

    # TXT 리포트 생성
    blocks = [format_case_block(r) for r in results]
    report = "\n".join(blocks)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nSaved LLM-as-judge report to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()


