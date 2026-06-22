# 날씨 AI Agent 개발 기획서 (PLAN.md)

> 대상 과제: [`ASSIGNMENT.md`](./ASSIGNMENT.md) — "날씨 AI Agent 개발"
> 작성일: 2026-06-19
> 강의 맥락: Lecture 01 "AI 에이전트의 이해" — **생각·행동·관찰** 반복 루프의 데모 구현

---

## 1. 개요 및 목표

사용자가 도시 이름을 말하면 그 도시의 **내일 날씨**(기온·강수)를 한 문장으로 정리해 주고,
비가 오면 우산 안내를 덧붙이는 **날씨 에이전트**를 구현한다.

목표 동작 (과제 명세):
1. ① 질문에서 도시 이름 찾기 → ② 날씨 도구 호출 → ③ 결과를 한 문장으로 정리 → ④ 우산이 필요하면 한마디 덧붙이기
2. 출력 예시: `"내일 서울은 12°C에 비가 와요. 우산 챙기세요! ☂️"`

이 흐름은 강의에서 가르친 **두뇌(LLM) · 도구 · 생각-행동-관찰 루프**를 그대로 코드로 옮긴 것이다.
과제의 "Skill"은 강의의 **도구(Tool)** 개념과 동일하며, 본 기획에서는 **Claude Haiku가 호출하는 LangChain Tool**로 구현한다.

---

## 2. 확정된 기술 선택

| 항목 | 선택 | 근거 |
|------|------|------|
| 날씨 API | **Open-Meteo** | 무료·API 키 불필요, 지오코딩(도시명→좌표) + 예보를 한 세트로 제공 |
| LLM | **Claude Haiku** (`claude-haiku-4-5`) | 과제 지정. tool use 지원, 빠르고 저렴 |
| 에이전트 프레임워크 | **LangGraph 커스텀 StateGraph** | 강의의 `생각→행동→관찰` while 루프를 노드로 명시적 시각화 |
| Backend | **Python + FastAPI** | 과제 지정 |
| Frontend | **Vanilla HTML/CSS/JS** (단일 페이지 채팅) | 빌드 도구 없이 입문 강의에 적합 |
| 테스트 | **단위 + 통합** (pytest / Vitest) | 외부 API는 mock, FastAPI 엔드포인트는 통합 테스트 |

---

## 3. 시스템 아키텍처

```
┌─────────────────────────┐         POST /chat          ┌──────────────────────────────────┐
│  Frontend (Vanilla SPA)  │  ───────────────────────▶  │  Backend (FastAPI)                 │
│  - index.html            │   { "message": "..." }      │                                    │
│  - app.js (fetch)        │  ◀───────────────────────  │   ┌──────────────────────────────┐ │
│  - styles.css            │   { "reply": "..." }        │   │ LangGraph StateGraph          │ │
└─────────────────────────┘                              │   │                              │ │
                                                         │   │  START → agent(생각) ──┐      │ │
                                                         │   │            ▲           │ 분기  │ │
                                                         │   │            │      tool_calls? │ │
                                                         │   │       (관찰)│           ├─yes─▶ tools(행동) ─┐
                                                         │   │            └───────────┘      │           │
                                                         │   │                  │ no          │           │
                                                         │   │                  ▼             └───────────┘
                                                         │   │                 END                         │
                                                         │   └──────────────────────────────┘ │
                                                         │            │ get_weather(city)        │
                                                         └────────────┼──────────────────────────┘
                                                                      ▼
                                                         ┌──────────────────────────────────┐
                                                         │  Open-Meteo API                    │
                                                         │  1) Geocoding: 도시명 → lat/lon     │
                                                         │  2) Forecast: lat/lon → 내일 예보   │
                                                         └──────────────────────────────────┘
```

**생각-행동-관찰 매핑**
- **생각(Reason)**: `agent` 노드 — Claude Haiku가 도시 이름을 추출하고 도구 호출 여부를 판단 (= 동작 ①)
- **행동(Act)**: `tools` 노드 — `get_weather` 도구 실행 (= 동작 ②)
- **관찰(Observe)**: tool 결과가 메시지로 추가되어 다시 `agent` 노드로 복귀
- **답변**: 더 이상 도구 호출이 없으면 한 문장 요약 + 우산 안내 생성 후 END (= 동작 ③④)

---

## 4. 디렉터리 구조

```
Assignment/harness/
├── ASSIGNMENT.md
├── PLAN.md                  ← 본 문서
├── backend/
│   ├── src/                 ← 프로덕션 코드만 (테스트 금지)
│   │   ├── __init__.py
│   │   ├── config.py        # 환경변수·모델 설정 (CLAUDE_API_KEY 매핑)
│   │   ├── weather.py       # 날씨 도구(Skill) — Open-Meteo 연동
│   │   ├── agent.py         # LangGraph StateGraph 정의
│   │   └── main.py          # FastAPI 앱 + /chat 엔드포인트 + CORS
│   ├── test/                ← 테스트 코드만
│   │   ├── test_weather.py
│   │   ├── test_agent.py
│   │   └── test_api.py
│   ├── pyproject.toml        # 의존성·도구 설정
│   └── README.md
└── frontend/
    ├── src/                 ← 프로덕션 코드만
    │   ├── index.html
    │   ├── app.js           # fetch + 메시지 렌더링
    │   └── styles.css
    ├── test/                ← 테스트 코드만
    │   └── app.test.js
    └── package.json         # Vitest 설정
```

> **과제 제약 준수**: `src` 폴더에는 테스트 코드를 절대 두지 않으며, 모든 테스트는 `backend/test`, `frontend/test`에 배치한다.

---

## 5. 백엔드 상세 설계

### 5.1 날씨 도구(Skill) — `weather.py`

LangChain `@tool` 데코레이터로 `get_weather(city: str)`를 정의한다. Claude Haiku가 이 도구를 호출한다.

**처리 흐름 (Open-Meteo, 2단계 호출):**

1. **지오코딩** — 도시명 → 위경도
   `GET https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ko&format=json`
   - 결과가 비면 → "도시를 찾을 수 없음" 메시지 반환 (LLM이 사용자에게 전달)

2. **예보** — 위경도 → 내일 날씨
   `GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code&timezone=auto`
   - `daily` 배열의 **index 1**이 내일 (index 0 = 오늘). `timezone=auto`로 현지 날짜 경계 보장.

**반환 형식 (LLM이 판단·요약하기 쉽도록 구조화):**
```python
{
  "city": "서울",
  "date": "2026-06-20",
  "temp_max": 12.0,
  "temp_min": 7.0,
  "precipitation_mm": 5.2,
  "precipitation_prob": 80,        # %
  "weather_desc": "비"             # weather_code를 도구 내부에서 한글로 매핑
}
```
- HTTP 통신은 `httpx` 사용. 타임아웃(예: 10초) 설정, 실패 시 명확한 에러 문자열 반환.
- **`weather_code`(WMO 0–99)는 직관적이지 않으므로 도구 내부에서 한글 설명(`weather_desc`)으로 매핑**한다. 원시 WMO 코드 해석을 LLM에 맡기면 Haiku가 불안정하게 디코딩할 수 있다. (예: `0`→"맑음", `61`→"비", `71`→"눈". 핵심 코드만 매핑하고 미정의 코드는 강수량 기반 기본값.)
- **우산 판단은 도구가 아니라 LLM이 수행**한다. 시스템 프롬프트에서 "강수확률 50% 이상 또는 강수량 0mm 초과면 우산을 권하라"고 지시하고, 도구는 원시 수치만 제공한다. (도구는 데이터, LLM은 표현/판단 — 역할 분리)

### 5.2 LangGraph 에이전트 — `agent.py`

강의의 `생각→행동→관찰` 루프를 **커스텀 StateGraph**로 명시적으로 구현한다.

```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_anthropic import ChatAnthropic

# 1) 모델 + 도구 바인딩 (API 키는 config.py의 env 브릿지로 주입 — 5.4 참조)
llm = ChatAnthropic(model="claude-haiku-4-5")
llm_with_tools = llm.bind_tools([get_weather])

# 2) 노드
async def agent_node(state: MessagesState):          # 생각
    msg = await llm_with_tools.ainvoke([SYSTEM_PROMPT, *state["messages"]])
    return {"messages": [msg]}

tool_node = ToolNode([get_weather])                  # 행동 + 관찰

# 3) 분기 라우팅 — 강의의 while 루프 분기를 "눈에 보이게" 직접 작성
def should_continue(state: MessagesState) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END

# 4) 그래프
graph = StateGraph(MessagesState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")
app_graph = graph.compile()
```

- **분기 라우팅을 `should_continue`로 직접 작성**한다. prebuilt `tools_condition`은 블랙박스이므로, "마지막 메시지에 `tool_calls`가 있으면 행동, 없으면 종료"라는 강의의 분기 로직을 명시적으로 드러낸다. (커스텀 StateGraph를 선택한 교육적 의도와 일치)
- **비동기 일관성**: `agent_node`는 `async` + `ainvoke`로 작성하고, 엔드포인트도 `await app_graph.ainvoke(...)`를 호출하여 이벤트 루프 블로킹을 피한다 (5.3 참조).
- **State**: LangGraph 기본 `MessagesState` (대화 메시지 리스트, `add_messages` reducer 자동 적용).
- **시스템 프롬프트**(`SYSTEM_PROMPT`)가 출력 규칙을 정의:
  - 도시 이름을 찾아 `get_weather` 도구를 호출할 것
  - 결과를 **한 문장**으로 친근하게 정리할 것 (예시 형식 제공)
  - 강수확률 50%↑ 또는 강수량 0mm↑면 우산 안내 + ☂️ 덧붙일 것
  - 날씨와 무관한 질문이면 도구 없이 정중히 안내할 것

### 5.3 FastAPI 엔드포인트 — `main.py`

```
POST /chat
  요청:  { "message": "내일 서울 날씨 어때?" }
  응답:  { "reply": "내일 서울은 최고 12°C에 비가 와요. 우산 챙기세요! ☂️" }

GET  /health  → { "status": "ok" }   # 헬스체크
```

- **엔드포인트는 `async def chat`** 으로 작성하고 `reply = await app_graph.ainvoke({"messages": [HumanMessage(message)]})` 호출 후 마지막 AI 메시지 텍스트를 `reply`로 반환한다. (동기 `.invoke()`를 `async def` 안에서 호출하면 이벤트 루프가 막히므로 `ainvoke` 사용 — 5.2의 비동기 노드와 일관)
- **CORS**: 프론트엔드(다른 포트)에서 호출하므로 `CORSMiddleware`로 `http://localhost:*` 허용 (개발용).
- Pydantic 모델로 요청/응답 스키마 정의.

### 5.4 설정 / 환경변수 — `config.py`

- **중요 이슈**: 부모 디렉터리 `.env`에 키가 **`CLAUDE_API_KEY`**로 저장되어 있으나, `ChatAnthropic`/Anthropic SDK 기본값은 **`ANTHROPIC_API_KEY`**이다.
- **해결 — 환경변수 브릿지**: `config.py`에서 `.env` 로드 후, `ChatAnthropic()` 생성 **전에** 다음과 같이 브릿지한다.
  ```python
  import os
  from dotenv import load_dotenv
  load_dotenv("../.env")  # 또는 적절한 경로
  os.environ.setdefault("ANTHROPIC_API_KEY", os.environ["CLAUDE_API_KEY"])
  ```
  이렇게 하면 `ChatAnthropic`이 표준 `ANTHROPIC_API_KEY`를 자동 인식하므로, 버전마다 다를 수 있는 키 인자명(`api_key` vs `anthropic_api_key`)에 의존하지 않는다. 기존 `.env`도 변경 불필요.
- `python-dotenv`로 `.env` 로드. 설정 검증·관리는 Pydantic `pydantic-settings`(`BaseSettings`) 사용 권장.

---

## 6. 프론트엔드 상세 설계

- **`index.html`**: 단일 페이지. 메시지 목록 영역 + 입력창 + 전송 버튼.
- **`app.js`**:
  - 전송 시 `fetch('http://localhost:8000/chat', { method:'POST', body: JSON.stringify({message}) })`
  - 응답 `reply`를 말풍선으로 렌더링. 로딩 상태("생각 중...") 표시. 에러 핸들링.
  - 렌더링·fetch 로직을 **테스트 가능한 순수 함수**로 분리 (예: `renderMessage`, `sendMessage`).
- **`styles.css`**: 간단한 채팅 UI 스타일.

---

## 7. 테스트 전략 (TDD)

**원칙**: 각 단계는 테스트를 먼저 작성(Red) → 구현(Green) → 정리(Refactor). 외부 API는 mock.

### 백엔드 (`backend/test`, pytest)
| 파일 | 범위 | 내용 |
|------|------|------|
| `test_weather.py` | 단위 | `get_weather` — 정상 응답, 도시 없음, API 오류. Open-Meteo는 `respx`/`pytest-httpx`로 mock |
| `test_agent.py` | 단위/통합 | 그래프가 도구를 호출하고 최종 메시지를 생성하는지. LLM은 mock 또는 도구 노드 단위 검증 |
| `test_api.py` | 통합 | `POST /chat` 엔드포인트 — `httpx.AsyncClient` + `ASGITransport`로 호출, 그래프는 mock |

### 프론트엔드 (`frontend/test`, Vitest)
| 파일 | 범위 | 내용 |
|------|------|------|
| `app.test.js` | 단위/통합 | 메시지 렌더링, `fetch` mock 후 응답 표시, 에러 표시. `jsdom`/`happy-dom` 환경 |

---

## 8. 의존성

**Backend (`pyproject.toml`)**
- 런타임: `fastapi`, `uvicorn[standard]`, `langgraph`, `langchain-anthropic`, `langchain-core`, `httpx`, `pydantic`, `pydantic-settings`, `python-dotenv`
- 테스트: `pytest`, `pytest-asyncio`, `pytest-httpx`(또는 `respx`)

**Frontend (`package.json`)**
- 테스트: `vitest`, `jsdom`(또는 `happy-dom`)
- 런타임 의존성 없음 (Vanilla)

> 정확한 버전은 구현 시점에 `langchain-dependencies` 가이드를 참고하여 최신 안정 버전으로 핀(pin)한다.

---

## 9. 개발 단계 (마일스톤)

| Phase | 내용 | 산출물 |
|-------|------|--------|
| **0** | 프로젝트 스캐폴딩 (디렉터리, `pyproject.toml`, `package.json`, `config.py`) | 실행 가능한 빈 골격 |
| **1** | 날씨 도구(Skill) TDD 구현 (Open-Meteo 2단계) | `weather.py` + `test_weather.py` 통과 |
| **2** | LangGraph StateGraph + 시스템 프롬프트 | `agent.py` + `test_agent.py` 통과 |
| **3** | FastAPI `/chat` 엔드포인트 + CORS | `main.py` + `test_api.py` 통과 |
| **4** | 프론트엔드 채팅 UI | `frontend/src/*` + `app.test.js` 통과 |
| **5** | E2E 수동 검증 (서버 기동 → 브라우저에서 대화) | 동작 시연 |

각 Phase는 의존 순서대로 진행하며, Phase 종료 시 해당 테스트가 모두 통과해야 다음으로 넘어간다.

---

## 10. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| **`.env`가 `.gitignore`에 없음** (현재 `CLAUDE_API_KEY` 노출 위험) | API 키 커밋·유출 | `.gitignore`에 `.env`, `*.env` 추가 권고. 키가 이미 커밋됐다면 회수/교체 권고 |
| 환경변수 이름 불일치 (`CLAUDE_API_KEY` vs `ANTHROPIC_API_KEY`) | LLM 인증 실패 | `config.py`에서 `api_key=` 명시 주입으로 해결 |
| 도시명 미발견 / 동음이의 도시 | 잘못된 날씨 | 지오코딩 `count=1` + `language=ko`, 결과 없으면 명확히 안내 |
| Open-Meteo 장애·타임아웃 | 응답 실패 | httpx 타임아웃 + 도구가 에러 문자열 반환 → LLM이 사용자에게 전달 |
| 날씨 무관 질문 | 엉뚱한 도구 호출 | 시스템 프롬프트로 날씨 질문에만 도구 사용하도록 가드 |
| 내일 기온이 max/min 두 값 | 출력 표현 모호 | 시스템 프롬프트에서 대표값(예: 최고기온) 위주로 간결히 표현 지시 |
| CORS 차단 | 프론트→백엔드 호출 실패 | `CORSMiddleware`로 개발 origin 허용 |

---

## 11. 실행 / 검증 방법

```bash
# 백엔드
cd backend && uvicorn src.main:app --reload --port 8000

# 프론트엔드 (정적 서버)
cd frontend/src && python -m http.server 5500
# 브라우저에서 http://localhost:5500 접속 후 "내일 서울 날씨 어때?" 입력

# 테스트
cd backend && pytest
cd frontend && npm test
```

검증 기준: 과제 출력 예시와 동일한 형태(`내일 {도시}는 {기온}에 {날씨}. {우산 안내}`)의 응답이 채팅창에 표시되면 성공.

---

## 12. advisor 검증 결과

상위 검토 모델(advisor)로 본 기획서를 검증했다. **전반 평가: 방향 변경 불필요, 실행 가능.**
Open-Meteo 2단계 호출, 모델 ID(`claude-haiku-4-5`), src/test 분리, 생각-행동-관찰 매핑, `.env` 보안 플래그는 모두 정확한 판단으로 확인되었다. 검토에서 나온 4개 지적과 **반영 내역**은 다음과 같다.

| # | 분류 | 지적 사항 | 반영 내역 |
|---|------|-----------|-----------|
| 1 | 🔴 런타임 | API 키 주입을 `ChatAnthropic(api_key=...)`로 단언했으나, 파라미터명이 버전에 따라 `anthropic_api_key`라 깨질 수 있음 | **§5.4를 환경변수 브릿지로 변경**: `os.environ.setdefault("ANTHROPIC_API_KEY", os.environ["CLAUDE_API_KEY"])`. 키 인자명 의존 제거 |
| 2 | 🔴 런타임 | `app_graph.invoke()`는 동기·블로킹 — `async def` 엔드포인트에서 호출 시 이벤트 루프 차단 | **§5.2·§5.3을 완전 비동기로 변경**: `agent_node`를 `async`+`ainvoke`, 엔드포인트를 `async def`+`await app_graph.ainvoke(...)` |
| 3 | 🟡 품질 | `weather_code`(WMO) 원시 코드를 LLM에 해석시키면 Haiku가 불안정하게 디코딩 | **§5.1 반환 형식 변경**: 도구 내부에서 `weather_code`→한글 `weather_desc`로 매핑하여 반환 |
| 4 | 🟡 품질 | prebuilt `tools_condition`은 블랙박스 — 커스텀 StateGraph를 고른 교육적 의도와 불일치 | **§5.2를 명시적 라우팅으로 변경**: `should_continue` 함수를 직접 작성해 분기 로직을 노출 |

**결론**: 차단 이슈(1·2)는 코드 실행 정확성에 직결되어 모두 기획에 반영 완료했고, 품질 이슈(3·4)도 함께 수용했다. 본 기획서는 구현 착수 가능한 상태다.
