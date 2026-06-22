# 날씨 AI Agent

도시명을 입력하면 그 도시의 **내일 날씨**를 한 문장으로 알려주고, 비가 오면 우산을 안내하는 에이전트.
강의 "생각 -> 행동 -> 관찰" 루프를 LangGraph로 구현한다.

## 구조

- `backend/` - FastAPI + LangGraph + Open-Meteo 날씨 도구 (Claude Haiku)
- `frontend/` - Vanilla SPA 채팅창

## 빠른 시작

```bash
# 1) 백엔드
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
uvicorn src.main:app --reload --port 8000

# 2) 프론트엔드 (새 터미널)
cd frontend/src
python -m http.server 5500
# 브라우저에서 http://localhost:5500 접속 -> "내일 서울 날씨 어때?"
```

## 테스트

```bash
cd backend && pytest
cd frontend && npx vitest run
```

백엔드 테스트는 외부 API/LLM을 mock 처리하므로 키 없이 실행할 수 있다.

## 환경변수

저장소 루트 `.env`의 `CLAUDE_API_KEY`를 사용한다. `backend/src/config.py`가 이를 SDK 표준 `ANTHROPIC_API_KEY`로 브릿지한다.
`.env`는 `.gitignore`에 포함되어 커밋되지 않는다.

## 자동 검증

에이전트가 자동으로 확인할 수 있는 항목:

- `backend` 전체 테스트
- `frontend` 전체 테스트
- 백엔드 기동 후 `GET /health` 스모크
- `.env`가 Git 추적 대상이나 히스토리에 없는지 확인

## 사람 검증

아래 검증은 유효한 `CLAUDE_API_KEY`, 실제 Claude 호출 비용, 브라우저 조작이 필요하므로 사람이 직접 수행한다.

### 실제 `/chat` 호출

백엔드가 `8000` 포트에서 실행 중인 상태에서:

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"내일 서울 날씨 어때?"}'
```

기대 형태: `{"reply":"내일 서울은 ...°C에 ... (비/맑음 등). (강수 시) 우산 챙기세요! ☂️"}`

### 브라우저 E2E

```bash
cd frontend/src
python -m http.server 5500
```

브라우저에서 `http://localhost:5500`에 접속한 뒤 다음을 확인한다.

- "내일 서울 날씨 어때?" 입력 시 "생각 중..." 표시 후 봇 말풍선에 한 문장 응답이 표시된다.
- 비 오는 도시 또는 예보라면 우산 안내와 `☂️`가 표시된다.
- 날씨와 무관한 질문(예: "점심 뭐 먹지?")에는 정중한 안내가 표시된다.
