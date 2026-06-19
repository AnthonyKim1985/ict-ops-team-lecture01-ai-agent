import pytest
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from src.agent import SYSTEM_PROMPT, app_graph, should_continue
from src.weather import get_weather


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
    assert "우산" in SYSTEM_PROMPT
    assert "get_weather" in SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_tool_node_executes_get_weather(httpx_mock):
    httpx_mock.add_response(
        json={"results": [{"name": "서울", "latitude": 37.566, "longitude": 126.978}]},
    )
    httpx_mock.add_response(
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

    graph = StateGraph(MessagesState)
    graph.add_node("tools", ToolNode([get_weather]))
    graph.add_edge(START, "tools")
    graph.add_edge("tools", END)
    tool_graph = graph.compile()

    ai = AIMessage(
        content="",
        tool_calls=[{"name": "get_weather", "args": {"city": "서울"}, "id": "call_1"}],
    )

    out = await tool_graph.ainvoke({"messages": [ai]})

    tool_msg = out["messages"][-1]
    assert "서울" in str(tool_msg.content)


def test_app_graph_is_compiled():
    assert hasattr(app_graph, "ainvoke")
