from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from src.config import settings
from src.weather import get_weather

SYSTEM_PROMPT = (
    "너는 친근한 날씨 비서야. 다음 규칙을 지켜.\n"
    "1) 사용자 메시지에서 도시 이름을 찾아 get_weather 도구를 호출해. "
    "이때 city 인자는 반드시 영문(로마자) 도시명으로 전달해. 예: 서울→Seoul, 부산→Busan, 제주→Jeju, 도쿄→Tokyo.\n"
    "2) 도구 결과를 바탕으로 '내일' 날씨를 한국어 한 문장으로 친근하게 정리해. "
    "예: '내일 서울은 12°C에 비가 와요.' 대표값은 최고기온 위주로 간결하게 말해.\n"
    "3) 강수확률이 50% 이상이거나 강수량이 0mm를 초과하면 우산 안내를 덧붙이고 끝에 ☂️ 를 붙여. "
    "예: '우산 챙기세요! ☂️'\n"
    "4) 도구가 error를 반환하면 그 내용을 사용자에게 정중히 그대로 전달해.\n"
    "5) 날씨와 무관한 질문이면 도구를 호출하지 말고 정중히 날씨만 도와줄 수 있다고 안내해."
)

llm = ChatAnthropic(model=settings.model_name)
llm_with_tools = llm.bind_tools([get_weather])
tool_node = ToolNode([get_weather])


async def agent_node(state: MessagesState) -> dict:
    message = await llm_with_tools.ainvoke(
        [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    )
    return {"messages": [message]}


def should_continue(state: MessagesState) -> str:
    last_message = state["messages"][-1]
    return "tools" if getattr(last_message, "tool_calls", None) else END


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
    content = message.content
    if isinstance(content, str):
        return content.strip()

    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts).strip()


async def run_agent(message: str) -> str:
    result = await app_graph.ainvoke({"messages": [HumanMessage(content=message)]})
    return _extract_text(result["messages"][-1])
