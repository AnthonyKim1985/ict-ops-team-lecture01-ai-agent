# TASK-3: FastAPI `/chat` 엔드포인트 — `main.py`

> **시작 브랜치:** `feat/fastapi-chat` (TASK-2 머지 후 `git switch main && git pull && git switch -c feat/fastapi-chat`)
> **이 문서만 보고 개발할 수 있도록 구성됨.** 외부 참조는 맨 아래 "참조" 절에만.

## 선행 작업 (TASK-0 · TASK-2 산출물 — 이미 존재해야 함)

- **`backend/src/main.py`** (TASK-0): 현재 `/health`만 있는 FastAPI 앱. 이 태스크가 **이 파일을 수정/확장**한다.
  ```python
  from fastapi import FastAPI
  from src.config import settings
  app = FastAPI(title="날씨 AI Agent")

  @app.get("/health")
  async def health() -> dict:
      return {"status": "ok"}
  ```
- **`src.agent.run_agent`** (TASK-2): `async def run_agent(message: str) -> str`. 사용자 입력 한 줄 → 최종 답변 텍스트.
- **`backend/test/conftest.py`** (TASK-0): 더미 `ANTHROPIC_API_KEY` 주입(테스트 import 안정성). **이 태스크 테스트도 이에 의존**.
- 의존성 `fastapi`, `httpx` 설치됨.

## 목표

`POST /chat`을 추가한다. 요청의 `message`를 `run_agent`로 처리해 `reply`로 반환. 프론트엔드(다른 포트)에서 호출하므로 **CORS** 허용. `/health`는 유지.

```
POST /chat
  요청:  { "message": "내일 서울 날씨 어때?" }
  응답:  { "reply": "내일 서울은 12°C에 비가 와요. 우산 챙기세요! ☂️" }

GET  /health → { "status": "ok" }   (TASK-0에서 이미 존재)
```

> **비동기:** 엔드포인트는 `async def`, 내부에서 `await run_agent(...)`. (동기 호출은 이벤트 루프를 막으므로 금지.)

## 수정/생성 파일

```
backend/src/main.py        ← 수정 (/chat, CORS, Pydantic 모델 추가)
backend/test/test_api.py   ← 신규 (테스트 — src에 두지 말 것)
```

---

## 단계별 작업 (TDD)

> **테스트 전략:** 실제 에이전트(=Claude API)를 부르지 않는다. `httpx.AsyncClient` + `ASGITransport`로 앱을 인-프로세스 호출하고, **`src.main.run_agent`를 monkeypatch**해 가짜 응답을 반환시킨다. (그래서 엔드포인트는 모듈 전역 `run_agent`를 호출 시점에 조회해야 한다 — 아래 구현이 그렇게 돼 있음.)

### Step 1: 실패 테스트 작성 — `backend/test/test_api.py`

```python
import httpx
import pytest
from httpx import ASGITransport

import src.main
from src.main import app


@pytest.mark.asyncio
async def test_chat_returns_reply(monkeypatch):
    async def fake_run_agent(message: str) -> str:
        assert message == "내일 서울 날씨 어때?"
        return "내일 서울은 12°C에 비가 와요. 우산 챙기세요! ☂️"

    monkeypatch.setattr(src.main, "run_agent", fake_run_agent)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={"message": "내일 서울 날씨 어때?"})

    assert resp.status_code == 200
    assert resp.json() == {"reply": "내일 서울은 12°C에 비가 와요. 우산 챙기세요! ☂️"}


@pytest.mark.asyncio
async def test_chat_validation_error_on_missing_message():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={})  # message 누락
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_health_still_ok():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_cors_headers_present(monkeypatch):
    async def fake_run_agent(message: str) -> str:
        return "ok"

    monkeypatch.setattr(src.main, "run_agent", fake_run_agent)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/chat",
            json={"message": "테스트"},
            headers={"Origin": "http://localhost:5500"},
        )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5500"
```

### Step 2: 테스트 실패 확인

```bash
cd backend && pytest test/test_api.py -v
```
기대: `/chat` 404 또는 CORS 헤더 없음으로 실패.

### Step 3: 구현 — `backend/src/main.py` (전체 교체)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import settings  # noqa: F401  (설정 로드 보장)
from src.agent import run_agent

app = FastAPI(title="날씨 AI Agent")

# CORS: 프론트엔드가 다른 포트(localhost)에서 호출하므로 개발용으로 localhost 허용
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    reply = await run_agent(req.message)
    return ChatResponse(reply=reply)
```

> **monkeypatch가 동작하는 이유:** `chat`이 모듈 전역 이름 `run_agent`를 호출 시점에 조회하므로, 테스트가 `src.main.run_agent`를 교체하면 그 가짜가 호출된다.

### Step 4: 테스트 통과 확인

```bash
cd backend && pytest test/test_api.py -v
```
기대: 4 passed.

### Step 5: 전체 회귀 + 기동 스모크

```bash
cd backend && pytest -v                          # TASK-0/1/2/3 모두 통과
uvicorn src.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/health             # {"status":"ok"}
kill %1
```

### Step 6: 커밋

```bash
git add backend/src/main.py backend/test/test_api.py
git commit -m "feat: POST /chat 엔드포인트 + CORS + 통합 테스트"
```

---

## 완료 기준 (Definition of Done)

- [ ] `pytest test/test_api.py` → 4 passed (reply / 422 / health / CORS)
- [ ] `POST /chat`이 `{"reply": "..."}` 반환, `message` 누락 시 422
- [ ] `CORSMiddleware`로 localhost origin 허용(응답에 `access-control-allow-origin`)
- [ ] `/health` 유지
- [ ] 전체 `pytest` 회귀 통과, 커밋 완료

## 다음 태스크에 넘기는 인터페이스 (TASK-4가 의존)

- 백엔드 서버: `uvicorn src.main:app --port 8000` (CWD = `backend/`).
- `POST http://localhost:8000/chat` — body `{"message": string}` → `{"reply": string}`.
- CORS: `http://localhost:*`, `http://127.0.0.1:*` 허용.

---

## 참조 (외부 문서/스킬 — 필요 시에만)

- `PLAN.md` §5.3(엔드포인트 상세), §10(CORS 리스크).
- `langchain-fundamentals` / FastAPI 공식 문서 — `ASGITransport` 테스트 패턴 확인용.
