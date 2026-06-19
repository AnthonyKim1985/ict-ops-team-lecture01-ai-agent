# TASK-5: 통합 · 문서화 · E2E 검증

> **시작 브랜치:** `chore/integration-e2e` (TASK-4 머지 후 `git switch main && git pull && git switch -c chore/integration-e2e`)
> **이 문서만 보고 개발할 수 있도록 구성됨.** 외부 참조는 맨 아래 "참조" 절에만.

## 선행 작업 (TASK-0~4 산출물 — 모두 머지되어 있어야 함)

- 백엔드: `backend/src/{config,weather,agent,main}.py` + `backend/test/{conftest,test_health,test_weather,test_agent,test_api}.py`, `pyproject.toml`.
- 프론트: `frontend/src/{index.html,app.js,styles.css}` + `frontend/test/app.test.js`, `package.json`, `vitest.config.js`.
- 백엔드 `/chat` 계약: `POST http://localhost:8000/chat` body `{"message"}` → `{"reply"}`.
- 프론트 정적 서빙: `cd frontend/src && python -m http.server 5500`.

## 목표

전체를 묶어 **동작을 검증**하고, 실행 방법을 **README로 문서화**한다. 에이전트가 자동으로 할 수 있는 검증과 사람이 해야 하는 검증을 명확히 구분한다.

## 만들 파일

```
backend/README.md     ← 신규
frontend/README.md    ← 신규
Assignment/README.md  ← 신규 (전체 실행 가이드)
```

---

## A. 에이전트가 자동으로 실행/검증 가능한 단계

### Step A1: 백엔드 전체 테스트

```bash
cd /Users/anthonykim/Workspace/SlideWorkspace/lecture01_ai_agent/Assignment/backend
pytest -v
```
기대: TASK-0(2) + TASK-1(3) + TASK-2(5) + TASK-3(4) = **14 passed** (정확한 개수는 구현에 따라 ±, 모두 통과해야 함).

### Step A2: 프론트엔드 전체 테스트

```bash
cd ../frontend
npx vitest run
```
기대: 4 passed.

### Step A3: 백엔드 기동 + `/health` 스모크 (네트워크/키 불필요)

```bash
cd ../backend
uvicorn src.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/health   # 기대: {"status":"ok"}
# (서버는 A5 사람 검증까지 살려두거나, 여기서 kill %1)
```

### Step A4: `.env` 보안 점검 (키가 커밋된 적 없는지 확인)

> `.env`는 git 루트 `.gitignore`에 이미 포함돼 있다(확인됨). 따라서 할 일은 "gitignore 추가"가 아니라 **과거에 키가 커밋된 적 없는지 확인**이다.

```bash
cd /Users/anthonykim/Workspace/SlideWorkspace/lecture01_ai_agent
git ls-files .env            # 기대: (빈 출력) — 추적되지 않음
git log --all -- .env        # 기대: (빈 출력) — 히스토리에 없음
```
- 둘 다 비어 있으면 OK.
- **만약** `.env`가 추적되거나 히스토리에 있으면: 키 노출이므로 README에 경고를 남기고 사용자에게 **키 회수/재발급**을 권고(이력 제거는 사용자 결정 필요).

---

## B. 사람이 해야 하는 단계 (실제 Claude 호출 = 비용/키 필요, 브라우저 조작)

> 에이전트는 이 단계를 "검증 완료"로 보고하지 말 것. **유효한 `CLAUDE_API_KEY`가 `.env`에 있어야** 하고, 실제 Claude Haiku 호출 비용이 발생하며, 브라우저 상호작용이 필요하다. 아래는 사람이 따라 할 절차다.

### Step B1: 실제 `/chat` 호출 (실제 LLM)

```bash
# 백엔드가 8000에서 떠 있는 상태에서:
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"내일 서울 날씨 어때?"}'
```
기대: `{"reply":"내일 서울은 ...°C에 ... (비/맑음 등). (강수 시) 우산 챙기세요! ☂️"}` 형태.

### Step B2: 브라우저 E2E

```bash
cd Assignment/frontend/src && python -m http.server 5500
```
- 브라우저에서 `http://localhost:5500` 접속.
- "내일 서울 날씨 어때?" 입력 → "생각 중..." 표시 후 봇 말풍선에 한 문장 응답.
- 비 오는 도시(예보에 따라)면 우산 안내 + ☂️ 확인.
- 날씨 무관 질문("점심 뭐 먹지?")이면 정중한 안내(도구 미호출) 확인.

**검증 기준(과제):** `내일 {도시}는 {기온}에 {날씨}. {우산 안내}` 형태가 채팅창에 표시되면 성공.

---

## C. 문서화

### Step C1: `backend/README.md`

````markdown
# 백엔드 (날씨 AI Agent)

FastAPI + LangGraph(Claude Haiku) + Open-Meteo.

## 설치
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
```

## 환경변수
- 키는 저장소 루트 `lecture01_ai_agent/.env`의 `CLAUDE_API_KEY`를 사용한다.
- `src/config.py`가 이를 SDK 표준 `ANTHROPIC_API_KEY`로 브릿지한다(코드/.env 수정 불필요).

## 실행
```bash
uvicorn src.main:app --reload --port 8000
```

## 테스트
```bash
pytest -v          # 외부 API/LLM은 모두 mock. 키 없이도 통과.
```

## 엔드포인트
- `GET /health` → `{"status":"ok"}`
- `POST /chat` body `{"message": "..."}` → `{"reply": "..."}`
````

### Step C2: `frontend/README.md`

````markdown
# 프론트엔드 (날씨 AI Agent)

Vanilla HTML/CSS/JS 단일 페이지 채팅.

## 실행 (정적 서버)
```bash
cd frontend/src
python -m http.server 5500
# 브라우저: http://localhost:5500  (백엔드가 8000에서 떠 있어야 함)
```

## 테스트
```bash
cd frontend
npm install          # 최초 1회 (vitest, jsdom)
npx vitest run
```
````

### Step C3: `Assignment/README.md`

````markdown
# 날씨 AI Agent

도시명을 입력하면 그 도시의 **내일 날씨**를 한 문장으로 알려주고, 비가 오면 우산을 안내하는 에이전트.
강의 "생각 → 행동 → 관찰" 루프를 LangGraph로 구현.

## 구조
- `backend/`  — FastAPI + LangGraph + Open-Meteo 날씨 도구 (Claude Haiku)
- `frontend/` — Vanilla SPA 채팅창

## 빠른 시작
```bash
# 1) 백엔드
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
uvicorn src.main:app --reload --port 8000

# 2) 프론트엔드 (새 터미널)
cd frontend/src && python -m http.server 5500
# 브라우저에서 http://localhost:5500 접속 → "내일 서울 날씨 어때?"
```

## 테스트
```bash
cd backend && pytest          # 백엔드 (mock 기반, 키 불필요)
cd frontend && npx vitest run # 프론트
```

## 환경변수
저장소 루트 `.env`의 `CLAUDE_API_KEY` 사용 (`src/config.py`가 `ANTHROPIC_API_KEY`로 브릿지).
`.env`는 `.gitignore`에 포함되어 커밋되지 않는다.
````

### Step C4: 커밋

```bash
cd /Users/anthonykim/Workspace/SlideWorkspace/lecture01_ai_agent/Assignment
git add backend/README.md frontend/README.md README.md
git commit -m "docs: 실행/테스트 가이드 README 추가 (백엔드/프론트/전체)"
```

---

## 완료 기준 (Definition of Done)

**에이전트 자동 (필수):**
- [ ] A1 `pytest` 전체 통과
- [ ] A2 `vitest run` 전체 통과
- [ ] A3 `GET /health` → `{"status":"ok"}`
- [ ] A4 `.env`가 추적/히스토리에 없음 확인 (있으면 README에 경고 + 사용자에게 키 재발급 권고)
- [ ] C1~C4 README 3종 작성 + 커밋

**사람 검증 (보고만, 에이전트가 "완료" 단정 금지):**
- [ ] B1 실제 `/chat` 호출이 과제 예시 형태 응답
- [ ] B2 브라우저에서 정상 대화 + 우산 안내 + 무관 질문 가드

---

## 참조 (외부 문서/스킬 — 필요 시에만)

- `PLAN.md` §9(마일스톤), §10(리스크: `.env` 보안), §11(실행/검증).
- `ASSIGNMENT.md` — 최종 검증 기준(출력 예시 형태).
- `verification-before-completion` 스킬 — 완료 보고 전 자가 점검.
