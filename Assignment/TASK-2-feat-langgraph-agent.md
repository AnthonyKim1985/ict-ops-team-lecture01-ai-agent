# TASK-2: LangGraph 에이전트 — `agent.py`

> **시작 브랜치:** `feat/langgraph-agent` (TASK-1 머지 후 `git switch main && git pull && git switch -c feat/langgraph-agent`)
> **이 문서만 보고 개발할 수 있도록 구성됨.** 외부 참조는 맨 아래 "참조" 절에만.

## 선행 작업 (TASK-0 · TASK-1 산출물 — 이미 존재해야 함)

- **`src.config.settings`** (TASK-0): `.model_name == "claude-haiku-4-5"`. import 시 `ANTHROPIC_API_KEY` 환경변수 보장.
- **`backend/test/conftest.py`** (TASK-0): 테스트 시 더미 `ANTHROPIC_API_KEY` 주입. → 이 덕분에 `agent.py`가 모듈 로드 시 `ChatAnthropic`을 생성해도 테스트 수집이 깨지지 않는다. **이 파일이 없으면 이 태스크의 테스트가 import 단계에서 전부 실패한다.**
- **`src.weather.get_weather`** (TASK-1): LangChain `@tool`, async. 호출 `await get_weather.ainvoke({"city": ...})`.
  - 성공 반환(7키): `{"city","date","temp_max","temp_min","precipitation_mm","precipitation_prob","weather_desc"}`
  - 실패 반환: `{"error": "..."}`
- 의존성 `langgraph`, `langchain-anthropic`, `langchain-core`, `pytest-httpx` 설치됨.

## 목표

강의의 **생각 → 행동 → 관찰** 루프를 **커스텀 LangGraph `StateGraph`**로 명시적으로 구현한다.
- **생각(agent 노드):** Claude Haiku가 도시명을 추출하고 도구 호출 여부 판단.
- **행동+관찰(tools 노드):** `get_weather` 실행 → 결과를 메시지로 추가 → 다시 agent 노드로.
- **분기 라우팅(`should_continue`):** 마지막 메시지에 `tool_calls`가 있으면 `tools`, 없으면 `END`. (prebuilt `tools_condition` 대신 **직접 작성**해 분기 로직을 노출 — 교육 의도.)
- **답변:** 도구 호출이 더 없으면 한 문장 요약 + (필요 시) 우산 안내 후 종료.

> **비동기 일관성:** `agent_node`는 `async` + `ainvoke`. 그래프 실행도 `await app_graph.ainvoke(...)`.

## 만들 파일

```
backend/src/agent.py        ← 신규 (프로덕션 코드)
backend/test/test_agent.py  ← 신규 (테스트 — src에 두지 말 것)
```

## 공개 인터페이스 (다운스트림 TASK-3가 그대로 의존하므로 정확히)

- `SYSTEM_PROMPT: str` — 출력 규칙 시스템 프롬프트.
- `should_continue(state) -> str` — `"tools"` 또는 `langgraph.graph.END`.
- `app_graph` — 컴파일된 그래프(`await app_graph.ainvoke({"messages": [...]})`).
- **`async def run_agent(message: str) -> str`** — 사용자 입력 한 줄을 받아 최종 답변 텍스트를 반환. (TASK-3 엔드포인트가 호출.)

---

## 단계별 작업 (TDD)

> **테스트 전략:** 실제 Claude API를 호출하지 않는다.
> - `should_continue`는 순수 함수 → 직접 단위 테스트.
> - `tools` 노드(행동/관찰)는 손수 만든 `tool_calls` 포함 `AIMessage`를 `ToolNode`에 흘려 검증. **이때 `get_weather`가 실제 Open-Meteo로 나가므로 `httpx_mock`으로 반드시 mock**한다(안 하면 라이브·플래키 테스트).
> - 전체 루프(LLM 포함)는 기본적으로 테스트하지 않는다(API 비용/불안정). 필요 시 `llm_with_tools`를 monkeypatch하는 선택적 테스트만.

### Step 1: 실패 테스트 작성 — `backend/test/test_agent.py`

```python
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END

from src.agent import should_continue, app_graph, SYSTEM_PROMPT
from src.weather import get_weather
from langgraph.prebuilt import ToolNode


def test_should_continue_routes_to_tools_when_tool_calls_present():
    ai = AIMessage(
        content="",
        tool_calls=[{"name": "get_weather", "args": {"city": "서울"}, "id": "call_1"}],
    )
    assert should_continue({"messages": [ai]}) == "tools"


def test_should_continue_routes_to_end_when_no_tool_calls():
    ai = AIMessage(content="내일 서울은 맑아요.")
    assert should_continue({"messages": [ai]}) == END


def test_system_prompt_mentions_umbrella_rule():
    # 우산/강수 규칙과 도구 사용 지침이 프롬프트에 들어있는지(회귀 방지)
    assert "우산" in SYSTEM_PROMPT
    assert "get_weather" in SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_tool_node_executes_get_weather(httpx_mock):
    # 행동/관찰 노드 검증: 손수 만든 tool_call을 ToolNode에 흘린다.
    # get_weather가 실제 네트워크로 나가므로 Open-Meteo를 mock한다.
    httpx_mock.add_response(
        url__startswith="https://geocoding-api.open-meteo.com/v1/search",
        json={"results": [{"name": "서울", "latitude": 37.566, "longitude": 126.978}]},
    )
    httpx_mock.add_response(
        url__startswith="https://api.open-meteo.com/v1/forecast",
        json={
            "daily": {
                "time": ["2026-06-19", "2026-06-20"],
                "temperature_2m_max": [20.0, 12.0],
                "temperature_2m_min": [14.0, 7.0],
                "precipitation_sum": [0.0, 5.2],
                "precipitation_probability_max": [10, 80],
                "weather_code": [1, 61],
            }
        },
    )

    tool_node = ToolNode([get_weather])
    ai = AIMessage(
        content="",
        tool_calls=[{"name": "get_weather", "args": {"city": "서울"}, "id": "call_1"}],
    )
    out = await tool_node.ainvoke({"messages": [ai]})

    tool_msg = out["messages"][-1]
    # ToolMessage.content는 도구 반환(dict)을 문자열로 직렬화한 것
    assert "서울" in str(tool_msg.content)


def test_app_graph_is_compiled():
    # 그래프가 컴파일되어 ainvoke를 갖는지(구조 스모크)
    assert hasattr(app_graph, "ainvoke")
```

> `url__startswith` 매처가 설치된 `pytest-httpx`에서 미지원이면, 매처를 빼고 응답을 FIFO 순서(지오코딩 → 예보)로 등록.

### Step 2: 테스트 실패 확인

```bash
cd backend && pytest test/test_agent.py -v
```
기대: `ImportError` (`agent.py` 없음).

### Step 3: 구현 — `backend/src/agent.py`

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode

from src.config import settings
from src.weather import get_weather

SYSTEM_PROMPT = SystemMessage(content=(
    "너는 친근한 날씨 비서야. 다음 규칙을 지켜.\n"
    "1) 사용자 메시지에서 도시 이름을 찾아 get_weather 도구를 호출해.\n"
    "2) 도구 결과를 바탕으로 '내일' 날씨를 한국어 한 문장으로 친근하게 정리해. "
    "예: '내일 서울은 12°C에 비가 와요.' (대표값은 최고기온 위주로 간결하게)\n"
    "3) 강수확률이 50% 이상이거나 강수량이 0mm를 초과하면 우산 안내를 덧붙이고 끝에 ☂️ 를 붙여. "
    "예: '우산 챙기세요! ☂️'\n"
    "4) 도구가 error를 반환하면 그 내용을 사용자에게 정중히 그대로 전달해.\n"
    "5) 날씨와 무관한 질문이면 도구를 호출하지 말고 정중히 날씨만 도와줄 수 있다고 안내해."
))

# 모델 + 도구 바인딩 (API 키는 src.config가 ANTHROPIC_API_KEY로 브릿지)
llm = ChatAnthropic(model=settings.model_name)
llm_with_tools = llm.bind_tools([get_weather])


async def agent_node(state: MessagesState) -> dict:          # 생각
    msg = await llm_with_tools.ainvoke([SYSTEM_PROMPT, *state["messages"]])
    return {"messages": [msg]}


tool_node = ToolNode([get_weather])                          # 행동 + 관찰


def should_continue(state: MessagesState) -> str:            # 분기 라우팅
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END


def build_graph():
    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


app_graph = build_graph()


def _extract_text(message) -> str:
    """AIMessage.content가 문자열 또는 content-block 리스트일 수 있으므로 텍스트만 추출."""
    content = message.content
    if isinstance(content, str):
        return content.strip()
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif isinstance(block, str):
            parts.append(block)
    return "".join(parts).strip()


async def run_agent(message: str) -> str:
    """사용자 입력 한 줄 → 최종 답변 텍스트."""
    result = await app_graph.ainvoke({"messages": [HumanMessage(content=message)]})
    return _extract_text(result["messages"][-1])
```

### Step 4: 테스트 통과 확인

```bash
cd backend && pytest test/test_agent.py -v
```
기대: 5 passed.

### Step 5: 전체 회귀 + 커밋

```bash
cd backend && pytest -v          # TASK-0/1/2 테스트 모두 통과
git add backend/src/agent.py backend/test/test_agent.py
git commit -m "feat: LangGraph StateGraph 에이전트(생각-행동-관찰) + run_agent + 테스트"
```

### (선택) Step 6: 실제 API 수동 확인

> 실제 Claude 호출이라 **비용 발생**. `.env`에 유효한 `CLAUDE_API_KEY`가 있어야 한다. 자동 테스트 아님.

```bash
cd backend && python -c "import asyncio; from src.agent import run_agent; print(asyncio.run(run_agent('내일 서울 날씨 어때?')))"
```
기대: "내일 서울은 ...°C에 ... (필요 시 우산 안내 ☂️)" 형태 한 문장.

---

## 완료 기준 (Definition of Done)

- [ ] `pytest test/test_agent.py` → 5 passed
- [ ] `should_continue`가 tool_calls 유무로 `"tools"`/`END` 분기
- [ ] `tools` 노드가 (mock된) `get_weather`를 실행하고 ToolMessage 생성
- [ ] `run_agent("...")`가 최종 텍스트를 반환(구조 검증)
- [ ] 전체 `pytest` 회귀 통과, 커밋 완료

## 다음 태스크에 넘기는 인터페이스 (TASK-3가 의존)

- **`async def run_agent(message: str) -> str`** — `from src.agent import run_agent`. TASK-3의 `/chat`이 `reply = await run_agent(req.message)`로 호출.
- `app_graph`, `should_continue`, `SYSTEM_PROMPT`도 export됨(직접 쓸 일은 거의 없음).

---

## 참조 (외부 문서/스킬 — 필요 시에만)

- `PLAN.md` §5.2(에이전트 상세), §3(생각-행동-관찰 매핑·그래프 다이어그램).
- `langgraph-fundamentals` 스킬 — `StateGraph`/`MessagesState`/`add_conditional_edges` 동작 확인용.
- `claude-api` 스킬 — 모델 ID(`claude-haiku-4-5`)·tool use 확인용.
