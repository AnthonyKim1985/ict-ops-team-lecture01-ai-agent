# CLAUDE.md

이 파일은 본 저장소에서 작업하는 Claude Code(및 미래의 Claude 인스턴스)를 위한 가이드입니다.
전체 설계 의도와 근거는 [`PLAN.md`](./PLAN.md)에, 과제 원문은 [`ASSIGNMENT.md`](./ASSIGNMENT.md)에 있습니다.

## 프로젝트 개요

사용자가 도시 이름을 말하면 그 도시의 **내일 날씨**(기온·강수)를 한 문장으로 요약하고, 비가 오면 우산 안내를 덧붙이는 **날씨 AI Agent**.
Lecture 01 "AI 에이전트의 이해"의 **생각(Reason) → 행동(Act) → 관찰(Observe)** 반복 루프를 코드로 옮긴 데모다.

- 출력 예시: `내일 서울은 12°C에 비가 와요. 우산 챙기세요! ☂️`
- LLM: **Claude Haiku** (`claude-haiku-4-5`) — tool use로 날씨 도구 호출
- 날씨 데이터: **Open-Meteo** (무료·API 키 불필요, 지오코딩 + 예보 2단계 호출)

## 디렉터리 구조

```
Assignment/harness/
├── PLAN.md                 # 설계 기획서(설계 결정의 단일 출처)
├── ASSIGNMENT.md           # 과제 원문
├── TASK-*.md               # Phase별 작업 명세(0~5)
├── backend/
│   ├── src/                # 프로덕션 코드 전용 (테스트 금지)
│   │   ├── config.py       # 환경변수 로드 + CLAUDE_API_KEY→ANTHROPIC_API_KEY 브릿지
│   │   ├── weather.py      # get_weather 도구(Skill) — Open-Meteo 연동
│   │   ├── agent.py        # LangGraph StateGraph (생각-행동-관찰 루프)
│   │   └── main.py         # FastAPI 앱: POST /chat, GET /health, CORS
│   └── test/               # pytest 테스트 전용
└── frontend/
    ├── src/                # index.html, app.js(fetch+렌더링), styles.css
    └── test/               # Vitest 테스트 전용 (app.test.js)
```

> **git 루트는 부모 디렉터리** `lecture01_ai_agent/`이며, `.env`(`CLAUDE_API_KEY`)도 거기에 있다. 작업 기준 디렉터리는 `Assignment/harness/`.

## 명령어

```bash
# --- 백엔드 (backend/ 에서 실행) ---
cd backend
pip install -e ".[test]"                      # 의존성 설치 (uv.lock도 있어 `uv sync`도 가능)
uvicorn src.main:app --reload --port 8000     # 서버 기동
pytest -v                                     # 테스트 (testpaths=test, asyncio_mode=auto)

# --- 프론트엔드 (frontend/ 에서 실행) ---
cd frontend
npm install
npm test                                      # vitest run (jsdom 환경)
python -m http.server 5500 --directory src    # 정적 서버 → http://localhost:5500

# --- 전체 ---
cd backend && pytest && cd ../frontend && npm test
```

외부 API(Open-Meteo)와 LLM은 테스트에서 모두 mock 처리되므로 **API 키 없이도 테스트는 통과해야 한다.**

## 아키텍처 핵심

`agent.py`의 LangGraph `StateGraph`가 강의의 while 루프를 노드로 명시한다:

```
START → agent(생각) ──tool_calls 있음?──┬─ yes → tools(행동) ─┐
          ▲                            │                    │
          └────────────(관찰)──────────┘── no → END          │
          └──────────────────────────────────────────────────┘
```

- **생각**: `agent` 노드 — Haiku가 도시명 추출 + 도구 호출 여부 판단
- **행동/관찰**: `tools` 노드(`ToolNode`)가 `get_weather` 실행 → 결과 메시지가 다시 `agent`로 복귀
- **종료**: 더 이상 tool_calls가 없으면 한 문장 요약 + 우산 안내 후 END

## 반드시 지킬 관례 (위반 시 동작/과제 제약 깨짐)

1. **`src/`에 테스트 코드를 절대 두지 않는다.** 테스트는 `backend/test`, `frontend/test`에만. (과제 명시 제약)
2. **비동기 일관성**: `agent` 노드와 엔드포인트는 모두 `async`/`ainvoke`/`await`. 동기 `.invoke()`를 `async def` 안에서 호출하면 이벤트 루프가 막힌다.
3. **환경변수 브릿지**: `.env`의 키 이름은 `CLAUDE_API_KEY`이고 Anthropic SDK 표준은 `ANTHROPIC_API_KEY`다. `config.py`가 `os.environ.setdefault`로 브릿지하므로 `ChatAnthropic(api_key=...)`에 키 인자명을 직접 의존하지 말 것. `.env`는 수정하지 않는다.
4. **역할 분리 — 도구는 데이터, LLM은 판단/표현**:
   - `get_weather`는 원시 수치(`temp_max`, `precipitation_mm`, `precipitation_prob`)와 한글 `weather_desc`만 반환한다.
   - **우산 판단은 도구가 아니라 시스템 프롬프트(LLM)가 한다** (강수확률 50%↑ 또는 강수량 0mm↑).
   - `weather_code`(WMO) 원시 코드는 LLM에 넘기지 말고 **도구 내부에서 한글로 매핑**한다(Haiku의 불안정한 디코딩 방지).
5. **Open-Meteo는 2단계 호출**: ① 지오코딩(도시명→lat/lon, `language=ko`, `count=1`) → ② 예보(`timezone=auto`, `daily` 배열 **index 1 = 내일**). httpx 타임아웃 설정, 실패 시 명확한 에러 문자열 반환.
6. **모델 ID는 `claude-haiku-4-5`** (과제 지정). 임의로 변경하지 말 것.

## 개발 방식

PLAN.md의 Phase 0~5 마일스톤을 따른다(스캐폴딩 → 날씨 도구 → 에이전트 → API → 프론트 → E2E).
각 기능은 **TDD**(Red → Green → Refactor)로 구현하고, 외부 API는 mock한다. Phase 종료 시 해당 테스트가 모두 통과해야 다음으로 넘어간다.
