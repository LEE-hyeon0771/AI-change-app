## AI-change-app

설계 변경(특히 VE 제안) 정보를 한 번에 관리하고, 현장 작업자에게 다국어로 설명해 주는 **엔드투엔드 RAG 애플리케이션**입니다.  
관리자는 엑셀/CSV/관리자 페이지를 통해 설계 변경 데이터를 등록하고, 작업자는 모바일/웹 UI에서 변경사항을 확인하고 각국 언어(한국어, 영어, 중국어, 베트남어, 우크라이나어)로 질의응답을 받을 수 있습니다.

---

## 1. 프로젝트 목적

- **설계VE / 설계변경 내역의 중앙 관리**
  - 기존에는 설계VE 제안 목록, 변경사항이 엑셀/문서로 흩어져 있어 검색·공유가 어렵고, 최신 내용이 어디에 있는지 알기 힘듦.
  - 이 프로젝트는 해당 데이터를 **벡터 DB(FAISS)** 로 통합하여, 질의응답 기반으로 빠르게 찾아볼 수 있도록 함.

- **현장 작업자 친화적인 다국어 설명**
  - 설계 변경 문서 자체는 기술적이고 한국어 중심이지만, 실제 현장은 다국적 인력으로 구성되는 경우가 많음.
  - 작업자용 페이지는 **한국어/영어/중국어/베트남어/우크라이나어** 5개 언어 탭을 제공하고, 선택한 언어로 설계 변경을 풀어서 설명.

- **관리자-작업자 간 변경사항 알림 플로우**
  - 관리자가 새로운 변경사항(VE 제안 포함)을 등록하면, 작업자 화면 상단에 **“새 설계변경 사항이 있습니다”** 알림이 자동 표시.
  - 작업자는 “변경사항 보기” 버튼으로 **기관명/사업명/제안명/제안일자/요청 발주처**를 바로 확인하고, 추가 질문은 챗봇으로 이어감.

- **기존 엑셀(xlsx) 기반 VE 데이터의 자동 인제스트**
  - “설계VE 상세내용 - VE제안 목록” 양식의 엑셀 파일을 그대로 `backend/app/data/` 에 넣고, 스크립트 한 번으로 **일괄 임베딩** 가능.
  - 헤더 행 탐지, 제안일자 파싱, LCC/가치향상 수치 → 설명 텍스트 변환까지 자동화하여 운영 부담 최소화.

---

## 2. 전체 아키텍처 개요

- **Frontend (Flutter)**
  - 앱 구조: `frontend_flutter/lib`
    - `main.dart` : 홈(역할 선택) 화면
    - `administer.dart` : 관리자용 설계 변경/VE 제안 등록 페이지
    - `worker.dart` : 작업자용 페이지 (알림 + 다국어 챗봇)
  - 타겟: 웹(Chrome) 및 모바일(에뮬레이터/실디바이스)

- **Backend (FastAPI + LangChain + OpenAI + FAISS)**
  - 디렉터리: `backend/app`
    - `core/`
      - `config.py` : 설정 및 .env 로딩, OpenAI 모델/키, 데이터 디렉터리
      - `models.py` : Pydantic 데이터 모델
    - `services/`
      - `vectorstore.py` : FAISS 기반 벡터 DB (임베딩, 저장, 검색)
      - `agent.py` : LangChain RAG 에이전트 (작업자용 다국어 챗봇)
      - `ingest_existing_data.py` : JSONL 기반 초기 데이터 적재
      - `ingest_ve_csv.py` : **엑셀/CSV VE 제안 목록 → 벡터DB** 인제스트
    - `main.py` : FastAPI 엔트리포인트 (관리자/작업자 API)

- **데이터/벡터 저장 위치**
  - `backend/data/faiss_index/index.faiss` : FAISS 인덱스
  - `backend/data/faiss_index/index.pkl` : 메타데이터/Docstore
  - `backend/data/change_log.jsonl` : 설계변경 기록(append only 로그)

---

## 3. 개발 Flow

### 3-1. 초기 세팅

1. **리포지토리 클론 후 루트로 이동**
   - 예: `D:\AI-change-app`

2. **Python 가상환경 생성 (Windows 기준)**
   - PowerShell:
     ```powershell
     cd D:\AI-change-app
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. **백엔드 의존성 설치**
   ```powershell
   cd backend
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. **OpenAI API 키 설정**
   - 루트에 `.env` 파일 생성:
     ```env
     OPENAI_API_KEY=sk-...본인키...
     ```
   - `backend/app/core/config.py` 에서 자동으로 `.env` 를 읽어 `settings.openai_api_key` 에 반영.

5. **Flutter 의존성 설치**
   ```bash
   cd frontend_flutter
   flutter pub get
   ```

### 3-2. 기존 VE 엑셀 데이터 인제스트 (선택)

엑셀 양식: **"설계VE 상세내용 - VE제안 목록"** (모든 파일의 컬럼 구성이 동일하다고 가정).

1. `backend/app/data/` 아래에 엑셀(xlsx) 파일 복사
   - 예:  
     - `backend/app/data/설계VE 상세내용 - VE제안 목록 (1).xlsx`  
     - `backend/app/data/설계VE 상세내용 - VE제안 목록 (2).xlsx` … 등

2. 인제스트 스크립트 실행
   ```powershell
   cd D:\AI-change-app
   .\.venv\Scripts\Activate.ps1
   cd backend
   python -m app.services.ingest_ve_csv app\data
   ```

   - 동작:
     - 디렉터리(`app\data`) 내의 모든 `.xlsx` / `.xlsm` / `.csv` 파일을 순회
     - 엑셀 상단의 여러 제목 행 중, `기관명,사업명,제안명,제안일자` 네 컬럼이 모두 포함된 행을 **헤더**로 자동 인식
     - 이후 행들을 `DesignChangeInput` 으로 변환하여 `add_design_change()` 로 저장
     - `change_log.jsonl` 과 `FAISS 인덱스` 에 누적
   - 로그 예시:
     ```text
     [DONE] 설계VE 상세내용 - VE제안 목록 (1).xlsx → 총 128건 성공, 0건 실패
     ```

3. 제안일자(날짜)가 `--` 등으로 비어 있는 경우
   - 파싱 에러를 내지 않고 기본값 `2000-01-01` 로 저장 (검색에는 영향 없음)
   - 실제 원본 값(`--`)은 description 텍스트 안에 그대로 유지

### 3-3. FastAPI 백엔드 실행

```powershell
cd D:\AI-change-app
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: `http://localhost:8000/docs`
- 헬스체크: `GET /health`
  - `openai_configured` 필드로 API 키 설정 여부 확인 가능

### 3-4. Flutter 프론트엔드 실행

#### Web (Chrome)

```powershell
cd D:\AI-change-app\frontend_flutter
flutter pub get
flutter run -d chrome
```

- `lib/api_config.dart` 의 `apiBaseUrl` 값이 백엔드 주소(`http://localhost:8000` 또는 `http://10.0.2.2:8000`)와 맞는지 확인.

#### Mobile (에뮬레이터 또는 연결 디바이스)

```powershell
cd D:\AI-change-app\frontend_flutter
flutter pub get
flutter run
```

---

## 4. 주요 기능 및 흐름

### 4-1. 관리자 페이지 (`AdministerPage`)

경로: `frontend_flutter/lib/administer.dart`

- **변경일(제안일자) 선택**
  - 상단에서 DatePicker로 날짜 선택.

- **제안정보 입력**
  - `제안명` (필수)
  - `기관명` (필수)
  - `사업명` (필수)
  - `요청 발주처` (선택)
  - `키워드` (선택)
  - `작성자` (선택)

- **생애주기비용(LCC) 절감효과 입력**
  - 개선전:
    - 건설사업 비용(백만원)
    - 유지관리 비용(백만원)
    - 계(백만원)
  - 개선후:
    - 건설사업 비용(백만원)
    - 유지관리 비용(백만원)
    - 계(백만원)
  - 절감액(백만원), 절감율(%)

- **가치향상효과 입력**
  - 개선전:
    - 성능점수(점)
    - 가치점수(점)
  - 개선후:
    - 성능점수(점)
    - 가치점수(점)

- **등록 버튼 동작**
  - 위 입력값을 기반으로 설명 텍스트(`description`)를 조합:
    - `[VE 제안명] ...`, `[생애주기비용(LCC) 절감효과 - 개선전] ...` 등의 섹션 포함
  - `POST /admin/changes` 로 전송:
    - `change_date` : 선택 날짜
    - `title` : 제안명
    - `description` : 조합된 텍스트
    - `author` : 작성자
    - `organization` : 기관명
    - `project_name` : 사업명
    - `client` : 요청 발주처
  - 백엔드는 이를 임베딩 후 FAISS / change_log 에 누적.

### 4-2. 작업자 페이지 (`WorkerPage`)

경로: `frontend_flutter/lib/worker.dart`

- **상단 알림 영역**
  - `GET /worker/latest-change` 를 15초 간격으로 폴링.
  - 응답 모델 `LatestChangeResponse`:
    - `has_change` : bool
    - `latest` : { `id`, `change_date`, `title`, `created_at`, `organization`, `project_name`, `client` }
  - 마지막으로 본 `id` 와 다를 경우:
    - `새 설계변경 사항이 있습니다.` 메시지 표시
  - 버튼:
    - `변경사항 보기` : Dialog 로 **기관명/사업명/제안명/제안일자/요청 발주처** 표시
    - `확인/읽음` : 마지막 확인한 변경 ID 업데이트

- **다국어 탭 + 챗봇 (UI 완전 현지화)**
  - `DefaultTabController` 로 5개 탭:
    - 한국어(ko), English(en), 中文(zh), Tiếng Việt(vi), Українська(uk)
  - 각 탭은 `WorkerChatTab(languageCode: 'ko' | 'en' | ...)` 인스턴스.
  - 탭에 따라 다음 UI 텍스트가 모두 변경됨:
    - 앱바 제목, 알림 문구, 버튼 라벨, 다이얼로그 제목/버튼, 입력 힌트 등
    - 각 언어별 문자열은 `_WorkerLanguage` 클래스에서 관리 (프론트 코드 내 하드코딩)

- **채팅 동작**
  - 사용자가 질문 입력 → `_sendMessage()` 호출:
    - UI 상에서 사용자 메시지 추가
    - `POST /worker/chat` 요청:
      ```json
      {
        "language": "ko",
        "question": "질문 내용",
        "history": [
          {"role": "user", "content": "..."},
          {"role": "assistant", "content": "..."}
        ]
      }
      ```
  - 응답(`WorkerChatResponse`):
    - `answer` : 선택 언어로 생성된 답변
    - `language` : 응답 언어 코드
    - `sources` : RAG 검색에 사용된 문서 ID/제목
  - 프론트는 답변을 **타이핑 스트리밍 효과**로 표시:
    - `Timer.periodic` 으로 짧은 간격(16ms)마다 2~3글자씩 추가하여,  
      실제 스트리밍처럼 보이도록 구현.

---

## 5. 백엔드 API 상세

### 5-1. 시스템/헬스체크

- `GET /health`
  - 응답:
    - `status` : `"ok"`
    - `time` : ISO8601 UTC 타임스탬프
    - `openai_configured` : bool

### 5-2. 관리자용 API

- `POST /admin/changes`
  - Request Body (`DesignChangeInput`):
    - `change_date` : `YYYY-MM-DD`
    - `title` : 제안명/변경 제목
    - `description` : 상세 설명 텍스트
    - `author` : 작성자 (선택)
    - `organization` : 기관명 (선택)
    - `project_name` : 사업명 (선택)
    - `client` : 요청 발주처 (선택)
  - 내부 동작:
    - OpenAI 임베딩(`text-embedding-3-small`) 생성
    - FAISS 인덱스에 `Document(page_content, metadata)` 로 추가
    - `change_log.jsonl` 에 JSON 한 줄 append
  - Response (`AdminChangeResponse`):
    - `success`: bool
    - `change`: `DesignChangeRecord` (id, created_at 등 포함)

### 5-3. 작업자용 API

- `GET /worker/latest-change`
  - 최신 `DesignChangeRecord` 기반 요약 반환.
  - 검색 기준:
    - 서버 메모리 캐시 `_LATEST_CHANGE`  
      없으면 `change_log.jsonl` 의 마지막 레코드를 읽어 복원.

- `POST /worker/chat`
  - Request Body (`WorkerChatRequest`):
    - `language` : `"ko" | "en" | "zh" | "vi" | "uk"`
    - `question` : 질문 텍스트
    - `worker_id` : 선택
    - `history` : 선택 (간단한 이전 대화)
  - 내부 동작:
    1. `vectorstore.get_retriever()` 로 유사 문서 k=5 검색
    2. 검색 문서들을 `_format_docs()` 로 포맷:
       - ID, 제목(제안명), 변경일(제안일자), 기관명, 사업명, 요청 발주처, 내용 요약 후보
    3. `ChatPromptTemplate` + `ChatOpenAI(gpt-4.1-mini)` 로 RAG 체인 실행
    4. 답변 맨 앞에 **기관명/사업명/제안명/제안일자/요청 발주처** 메타데이터 블록을  
       지정 언어로 표현하도록 시스템 프롬프트에서 강제
  - Response (`WorkerChatResponse`):
    - `answer` : 지정 언어로 생성된 설명
    - `language` : 언어 코드
    - `sources` : 사용된 문서의 `id`, `title` 목록

- **변경사항 보기 다국어 메타데이터**
  - `GET /worker/latest-change-translated?language=ko|en|zh|vi|uk`
    - 백엔드에서 최신 설계변경의 메타데이터(기관명/사업명/제안명/제안일자/요청 발주처)를 선택 언어로 번역.
    - `backend/app/services/agent.py` 의 `translate_latest_metadata_fields()` 가 OpenAI Chat 모델을 사용해 필드별로 번역/음역 수행.
    - JSON 파싱 오류를 피하기 위해 **5개 문장을 줄 단위로 번역**시키고, 순서대로 `organization/project_name/title/change_date/client` 에 매핑.
  - 프론트 (`worker.dart`) 에서는:
    - 라벨(예: “기관명”, “Project name”, “机构”) 은 `_WorkerLanguage` 에서 언어별로 정의.
    - 값(실제 기관명/사업명/제안명/요청 발주처/날짜) 은 위 번역 API 응답을 그대로 사용.
    - 따라서 **라벨 + 값 모두가 선택 언어로 표시**되며, 한국어 탭에서는 원문 그대로 노출.

### 5-4. LangChain 에이전트 (RAG 체인) 개요

- 위치: `backend/app/services/agent.py`
- 역할: **작업자 질문 → 관련 설계/VE 문서 검색 → 다국어 답변 생성** 전체 파이프라인을 한 번에 수행하는 RAG 체인.
- 구성 요소:
  - **Retriever**:  
    - `services/vectorstore.get_retriever()`  
    - FAISS 인덱스에서 질문과 가장 유사한 문서 상위 k개(k=5)를 검색.
  - **프롬프트 템플릿**:
    - 시스템 메시지에 역할/제약을 명시:
      - 설계 변경/VE 제안에 대해서만 답변
      - 제공된 문서를 근거로 사용할 것
      - 안전 관련 영향은 명확히 강조
      - **답변 맨 앞에 기관명/사업명/제안명/제안일자/요청 발주처를 요약 블록 형태로 표시**하도록 강제
    - 사용자 질문과 검색된 문서 목록(`context`)을 함께 LLM에 전달.
  - **LLM 설정**:
    - `ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)`
    - 낮은 temperature 로 사실/수치 왜곡을 줄이고, 지정 언어(`language_code`)로만 답변하도록 지시.
  - **LCEL 체인**:
    - `RunnableParallel` + `RunnableMap` 을 사용하여
      - 질문과 언어코드, 검색 문서를 동시에 준비
      - 문서 포맷팅 후 프롬프트에 바인딩
    - `prompt | llm | StrOutputParser()` 형태로 최종 문자열 답변 생성.
- 반환값:
  - `worker_chat()` 함수는 LLM 답변과 함께, 재검색한 문서들의 `id` / `title` 을 `sources` 로 반환하여,
    - UI 또는 추후 로깅/추적 시스템에서 “어떤 근거 문서를 참고했는지” 추적 가능하게 설계되어 있음.

---

## 6. 사용 기술 스택

- **Backend**
  - Python 3.10+
  - FastAPI 0.115
  - Uvicorn (ASGI 서버)
  - Pydantic v2
  - LangChain 0.3 (LCEL, RAG 체인)
  - langchain-openai, langchain-community
  - OpenAI:
    - Chat: `gpt-4.1-mini`
    - Embedding: `text-embedding-3-small`
  - FAISS (faiss-cpu)
  - OpenPyXL (xlsx 파싱)
  - python-dotenv

- **Frontend**
  - Flutter 3.x (Dart)
  - Material 3 UI
  - HTTP 패키지 (`package:http/http.dart`)

- **Infra / 기타**
  - 로컬 개발 환경 기준 (Windows 10+)
  - .venv 기반 Python 가상환경
  - Git + `.gitignore`:
    - `.venv`, `backend/data/`, `frontend_flutter/build/` 등은 기본적으로 Git 추적 제외

---

## 7. 성능 평가 (RAG & LLM-as-judge)

### 7-1. LLM-as-judge 기반 답변 품질 평가

- **스크립트 위치**: `backend/app/eval_llm_judge.py`
- **평가 절차**
  - 미리 정의한 소규모 테스트 케이스 리스트(`TEST_CASES`)를 기준으로, 각 케이스에 대해:
    - `POST /worker/chat` 호출 → 실제 RAG 답변(`answer`, `sources`) 획득
    - OpenAI Chat 모델(`gpt-4.1-mini`)을 **판사(judge)** 로 사용해, 아래 4개 지표를 1–5점으로 채점
  - 결과는 `rag_eval_llm_judge.txt` 로 저장되어, 케이스별 질문/답변/출처/점수/코멘트를 한 번에 확인 가능.
- **평가지표 (각 1–5점, 정수)**
  - **relevance**: 질문에 얼마나 직접/완전하게 답했는지
    - 5: 질문 의도와 핵심을 정확히 짚고 답변
    - 3: 일부만 답하거나 불필요한 내용이 섞임
    - 1: 대부분 엉뚱하거나 질문에 답하지 않음
  - **coverage**: 미리 정의한 `expected_key_points` 를 얼마나 잘 포함했는지
    - key point 를 “답변이 명시적으로 언급하거나, 데이터에 없다고 분명히 말하면(예: `미기재`, `Not specified`)” **커버한 것**으로 간주
    - 5: 거의 모든 key point 커버, 3: 절반 수준, 1: 거의 커버하지 못함
  - **structure**: 답변 구조가 “메타데이터 요약 블록 → 상세 설명” 패턴을 얼마나 잘 따르는지
    - 이상적 구조:
      - 맨 위에 기관명/사업명/제안명/제안일자/요청 발주처 등을 한눈에 볼 수 있는 **요약 블록**
      - 그 아래에 LCC 절감 효과, 배경 설명, 주의사항 등의 **설명 문단**
    - 5: 이 패턴이 명확히 지켜짐, 3: 일부 섞여 있지만 대략 구분 가능, 1: 구조가 거의 없어서 메타데이터와 설명이 뒤섞여 있음
  - **language_quality**: 선택된 언어 코드(ko/en/zh/vi/uk)에 맞춰 자연스럽고 이해하기 쉬운지
    - 5: 매우 자연스럽고 명확함, 3: 약간 어색하지만 의미 전달에는 문제 없음, 1: 문법/언어 선택 문제로 이해가 어렵거나 언어 코드와 맞지 않음
- **출력 코멘트**
  - `comment` 필드에 한국어로 “어떤 이유로 점수를 그렇게 줬는지”를 짧게 요약하여, 사람 검토 시 해석을 돕도록 설계.

### 7-2. RAG Retrieval 성능 평가

- **스크립트 위치**: `backend/app/eval_rag_retrieval.py`
- **테스트셋 포맷 (`rag_testset.json`)**
  - 루트: 리스트
  - 각 항목 예시:
    ```json
    {
      "id": "case_ko_01",
      "language": "ko",
      "question": "성남복정1 C3BL 설계 변경 내용과 LCC 절감 효과를 알려줘.",
      "gold_doc_ids": ["09715d1100d84681b14a3aa90ce4586d"],
      "type": "positive"   // "positive" | "multi" | "negative" | "oos"
    }
    ```
  - **positive/multi**: 정답 문서 ID(`gold_doc_ids`)가 하나 이상 있는 일반 RAG 케이스
  - **negative/oos**: 정답이 없는 케이스 (존재하지 않는 조합, 도메인 외 질문 등) → hallucination 여부만 평가.
- **평가지표 정의 (top-k 기준, 기본 k=5)**
  - **hit@k**
    - 정의: `gold_doc_ids` 집합과, RAG가 반환한 상위 k개 문서 ID 집합이 한 번이라도 겹치면 1, 아니면 0
    - 의미: “정답 문서가 최소 1개라도 top-k 안에 들어갔는지”
  - **precision@k**
    - 정의: \\(|gold ∩ pred\_top\_k| / |pred\_top\_k|\\)
    - 의미: “top-k 결과 중에서 진짜 정답 비율”
  - **recall@k**
    - 정의: \\(|gold ∩ pred\_top\_k| / |gold|\\)
    - 의미: “정답 문서들 중 얼마나 많이 top-k 안에 들어왔는지”
  - **hallucination rate** (negative/oos 전용)
    - negative/oos 케이스에서 **아무 문서도 반환하지 않으면 0**,  
      어떤 문서든 반환하면 1로 간주하여, 전체 비율을 계산
    - 의미: “정답이 ‘없어야 하는’ 질문에 대해, RAG가 억지로 문서를 끌어와 답한 비율”
- **출력**
  - 케이스별:
    - 질문, gold 문서 ID, 반환된 문서 ID(top-k),
    - `hit@k`, `precision@k`, `recall@k`, (negative/oos인 경우) `hallucination` 플래그
  - 요약:
    - 전체 케이스 수, positive/negative 개수
    - 평균 `hit@k` / `precision@k` / `recall@k`
    - negative/oos 케이스 기준 **hallucination rate**
  - 결과 파일: `rag_eval_retrieval.txt`

이 섹션을 참고하면, 프로젝트에 처음 들어온 사람도  
“어떤 기준(지표)으로 RAG와 답변 품질을 평가했고, 스크립트와 결과물이 어디에 있는지”를 한눈에 이해할 수 있다.

---

## 8. 향후 확장 아이디어

- **권한/인증**
  - 관리자/작업자 인증 및 역할 기반 접근 제어(RBAC)
  - JWT 또는 OAuth2 기반 토큰 도입

- **알림 채널 확장**
  - 현재는 작업자 화면 내 폴링 기반 알림
  - 향후 FCM(모바일 Push), 이메일, 사내 메신저(Slack/Teams) 연동 고려

- **추론 전략 고도화**
  - LangGraph / Agent Supervisor 도입해:
    - “설계 변경 자동 요약 리포트 작성”
    - “안전/품질 영향 여부 자동 태깅”
    - “특정 기간/기관별 VE 성과 집계” 등 복합 워크플로우 처리

- **관리자용 통계 대시보드**
  - VE 제안 건수, 채택률, LCC 절감액, 가치향상도 등 지표 시각화
  - 기관/사업/공종별 필터링과 Export 기능

이 README 만으로도 프로젝트 목적, 구조, 실행 방법을 바로 파악하고  
# AI-change-app