# SpeechPT — BE

FastAPI 기반 스피치 코칭 분석 플랫폼의 백엔드 서버입니다.  
발표 녹음(음성)과 발표 자료(PDF/PPT)를 업로드하면 AI가 발표를 분석하고, 분석 결과를 기반으로 RAG 채팅 피드백을 제공합니다.

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 웹 프레임워크 | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x |
| 데이터베이스 | PostgreSQL 15 + pgvector 확장 |
| 파일 스토리지 | AWS S3 (Presigned URL 방식) |
| 비동기 작업 큐 | AWS SQS |
| 인증 | JWT (Access/Refresh Token) + Google OAuth 2.0 |
| STT | faster-whisper (small, Korean, int8) |
| AI | OpenAI text-embedding-3-small (1536차원) + GPT |
| 컨테이너 | Docker / Docker Compose |

---

## 디렉토리 구조

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py            # 환경 변수 설정
│   │   ├── deps.py              # FastAPI 의존성 (JWT 인증 미들웨어)
│   │   ├── security.py          # JWT 생성/검증, bcrypt 비밀번호 해싱
│   │   ├── s3.py                # S3 head_object 검증 + JSON 객체 로드 유틸
│   │   └── sqs.py               # SQS 분석 작업 enqueue
│   ├── models/                  # SQLAlchemy ORM 모델
│   │   ├── user.py              # 사용자 (로컬 / Google OAuth)
│   │   ├── note.py              # 노트 (발표 세션 단위)
│   │   ├── analysis.py          # 분석 상태·진행률·대본 저장
│   │   ├── analysis_input.py    # 분석 입력 파일 S3 경로
│   │   ├── analysis_result.py   # 점수(content/delivery/pacing) + report_json
│   │   ├── analysis_section.py  # 슬라이드별 세부 피드백 (정규화)
│   │   ├── chat_session.py      # 노트별 채팅 세션
│   │   ├── chat_message.py      # 채팅 메시지 (role/content/citations_json)
│   │   ├── rag_chunk.py         # pgvector 임베딩 청크 (1536차원 VECTOR)
│   │   ├── practice_session.py  # 연습 세션
│   │   ├── practice_result.py   # 연습 결과
│   │   └── upload.py            # 파일 업로드 메타데이터 (S3 버킷/키/상태)
│   ├── routers/                 # API 라우터
│   │   ├── auth.py              # 로그인 / Google OAuth 콜백 / JWT 갱신
│   │   ├── note.py              # 노트 CRUD
│   │   ├── upload.py            # S3 Presigned URL 발급 + 업로드 완료 마킹
│   │   ├── analysis.py          # 분석 트리거·상태·결과 조회·워커 결과 제출
│   │   └── chat.py              # RAG 채팅 (일반 응답 / SSE 스트리밍)
│   ├── schemas/                 # Pydantic 요청/응답 스키마
│   │   ├── analysis.py
│   │   ├── chat.py
│   │   └── practice.py
│   ├── services/                # 핵심 비즈니스 로직
│   │   ├── stt_service.py       # faster-whisper STT (WAV 자동 변환 포함)
│   │   ├── audio_preprocess.py  # 오디오 전처리 유틸
│   │   ├── report_builder.py    # 워커 report.json → DB 저장 형식 변환
│   │   ├── rag_indexer.py       # 분석 결과 → rag_chunks 임베딩 인덱싱
│   │   ├── chat_rag.py          # 의도 분류(룰 기반) + RAG 검색 + LLM 답변
│   │   ├── chunk_builder.py     # 7종 RAG 청크 생성 (슬라이드/발화/피드백 등)
│   │   ├── suggestions.py       # 분석 결과 기반 추천 질문 생성
│   │   ├── openai_client.py     # OpenAI API 래퍼 (embed/chat/stream)
│   │   ├── auth_service.py      # 인증 서비스 유틸
│   │   └── user_service.py      # 사용자 조회 유틸
│   ├── db.py                    # SQLAlchemy 엔진/세션 설정
│   └── main.py                  # FastAPI 앱 + RAG 폴러 백그라운드 태스크
├── schema.sql                   # DB 전체 스키마 (참고용)
├── docker-compose.yml           # 로컬 개발용 PostgreSQL (pgvector 이미지)
├── Dockerfile                   # 서버 컨테이너 이미지
└── requirements.txt             # Python 패키지 목록
```

---

## API 엔드포인트

### 인증 — `/auth`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/auth/oauth/login` | Google OAuth 인증 페이지로 리다이렉트 |
| GET | `/auth/oauth/callback` | OAuth 코드 교환 → JWT 발급 → 프론트엔드로 리다이렉트 |
| POST | `/auth/login` | 이메일/비밀번호 또는 Google 계정 로그인 |
| POST | `/auth/refresh` | Access Token 갱신 (Refresh Token 사용) |
| GET | `/auth/me` | 현재 로그인 사용자 정보 조회 |

### 노트 — `/notes`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/notes` | 내 노트 목록 조회 |
| POST | `/notes` | 노트 생성 |
| GET | `/notes/{id}` | 노트 상세 조회 |
| PATCH | `/notes/{id}` | 노트 제목/설명 수정 |
| DELETE | `/notes/{id}` | 노트 삭제 (연관 데이터 CASCADE) |

### 파일 업로드 — `/uploads`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/uploads/presign` | S3 Presigned PUT URL 발급 (문서/음성) |
| POST | `/uploads/complete` | 업로드 완료 마킹 (status → uploaded) |
| GET | `/uploads` | 업로드 목록 조회 |

지원 형식
- **문서**: PDF, PPT, PPTX
- **음성**: MP3, WAV, M4A

### 분석 — `/analyses`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/notes/{id}/analyses` | 분석 시작 (SQS enqueue, status=queued) |
| GET | `/analyses/{id}/status` | 분석 진행 상태 조회 (progress, stage) |
| GET | `/analyses/{id}/result` | 분석 결과 조회 |
| GET | `/notes/{id}/analyses/latest/result` | 노트의 최신 분석 결과 |
| GET | `/notes/{id}/analyses/history` | 분석 히스토리 (점수 시계열) |
| POST | `/analyses/{id}/submit-result` | AI 워커가 분석 결과 제출 |

분석 단계 (stage): `ingest → stt → keypoint → alignment → ae_feature → ae_probe → llm → finalize → finished`

### 채팅 (RAG) — `/chat-sessions`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/notes/{id}/chat` | 채팅 세션 조회 (없으면 자동 생성) |
| GET | `/notes/{id}/chat/suggestions` | 분석 결과 기반 추천 질문 목록 |
| POST | `/chat-sessions/{id}/messages` | 메시지 저장 |
| DELETE | `/chat-sessions/{id}/messages` | 대화 초기화 |
| POST | `/chat-sessions/{id}/reply` | AI 답변 생성 (JSON) |
| POST | `/chat-sessions/{id}/stream-reply` | AI 답변 생성 (SSE 스트리밍) |

---

## 핵심 서비스 상세

### RAG 파이프라인 (`rag_indexer.py`, `chunk_builder.py`, `chat_rag.py`)

분석 완료 후 7종의 청크로 분해하여 OpenAI 임베딩(1536차원)을 생성, `rag_chunks` 테이블에 저장합니다.

| 청크 타입 | 내용 |
|-----------|------|
| `slide_text` | 슬라이드 정적 내용 (역할, 누락 키포인트) |
| `transcript_segment` | 슬라이드별 발화 대본 구간 |
| `feedback_slide` | 슬라이드별 AI 피드백 |
| `feedback_overall` | 전체 요약·강점·개선점 |
| `metric` | 점수 카드 (content/delivery/pacing) |
| `practice_plan` | 연습 계획 제안 |
| `progress_delta` | 이전 분석 대비 변화 비교 |

채팅 시 룰 기반 의도 분류(5종) → 강제 포함 청크 + cosine 유사도 top-k 검색 → LLM 컨텍스트 패킹 → GPT 답변 생성 + 인용 마커 반환.

### STT 서비스 (`stt_service.py`)

- faster-whisper `small` 모델, CPU int8, 한국어
- WAV 외 형식(MP3, M4A, MP4 등)은 PyAV로 16kHz mono WAV 자동 변환
- 반환: 전체 텍스트 + 단어별 타임스탬프 및 신뢰도

---

## DB 스키마

```
users
  └─ notes
       ├─ uploads        (S3 파일 메타데이터)
       ├─ analyses
       │    ├─ analysis_inputs   (S3 파일 경로)
       │    ├─ analysis_results  (점수 + report_json)
       │    ├─ analysis_sections (슬라이드별 피드백, 정규화)
       │    └─ rag_chunks        (pgvector 임베딩 1536차원, HNSW 인덱스)
       └─ chat_sessions
            └─ chat_messages     (citations_json 포함)
```

---

## 로컬 실행 방법

### 1. 사전 준비
- Python 3.10+, Docker
- AWS 계정 (S3 버킷, SQS 표준 큐)
- OpenAI API 키
- Google OAuth 2.0 클라이언트 ID/Secret

### 2. 환경 변수 설정

`backend/.env` 파일을 생성합니다. 필요한 키 목록은 아래를 참고하세요.  
실제 값은 팀 내부에서 별도로 공유하며, `.env` 파일은 `.gitignore`에 등록되어 있어 저장소에 올라가지 않습니다.

```
DATABASE_URL              # PostgreSQL 연결 문자열
SECRET_KEY                # JWT 서명 키
ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS
GOOGLE_OAUTH_CLIENT_ID
GOOGLE_OAUTH_CLIENT_SECRET
GOOGLE_OAUTH_REDIRECT_URI
FRONTEND_URL              # OAuth 콜백 후 리다이렉트될 프론트엔드 주소
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
S3_BUCKET                 # 업로드 파일 저장 버킷
ANALYSIS_QUEUE_URL        # SQS 큐 URL
OPENAI_API_KEY
CORS_ALLOWED_ORIGINS      # 쉼표 구분 허용 오리진 목록
UPLOAD_STORAGE            # local 또는 s3
```

### 3. PostgreSQL 실행

```bash
cd backend
docker-compose up -d
```

pgvector가 프리설치된 `pgvector/pgvector:pg15` 이미지를 사용합니다.

### 4. 서버 실행

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

서버 시작 시 자동으로 다음을 수행합니다:
- `pgvector` 확장 설치
- 신규 컬럼 마이그레이션 (`rag_indexed_at`, `citations_json`)
- 전체 테이블 생성 (`Base.metadata.create_all`)
- HNSW 임베딩 인덱스 생성
- RAG 폴러 백그라운드 태스크 시작

**API 문서**: http://localhost:8000/docs

---

## 분석 처리 흐름

```
사용자: PDF/PPT + 음성 파일 업로드
    → S3 Presigned PUT URL 발급 → 브라우저에서 S3에 직접 업로드
    → 업로드 완료 마킹 (status: uploaded)
    → POST /notes/{id}/analyses
         └─ analyses 행 INSERT (status=queued)
         └─ analysis_inputs 행 INSERT (S3 경로)
         └─ SQS enqueue (워커에게 작업 전달)
    ← 즉시 응답 (analysis_id 반환)

워커 (별도 프로세스):
    → SQS에서 메시지 수신
    → STT (faster-whisper) → 슬라이드 alignment → AE probe → LLM 피드백
    → POST /analyses/{id}/submit-result (결과 제출)
         └─ analysis_results 저장 (점수 + report_json)
         └─ analysis_sections 저장 (슬라이드별 정규화)
         └─ analyses 상태 → done

RAG 폴러 (20초 주기):
    → status=done, rag_indexed_at IS NULL인 분석 감지
    → 청크 생성 + OpenAI 임베딩 생성
    → rag_chunks 저장 (HNSW 인덱스)
    → rag_indexed_at 업데이트 → 채팅 활성화
```
