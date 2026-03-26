"""
StateGraph 커스텀 워크플로우 — Level 3 (도전)

create_deep_agent 대신 StateGraph로 직접 에이전트 그래프를 구성합니다.
이 파일의 create_graph_agent()를 agent.py에서 import하여 사용할 수 있습니다.

사용법 (agent.py에서):
    from graph.workflow import create_graph_agent
    agent = create_graph_agent(model, tools, system_prompt)
"""

import operator
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict


# ─── 상태 정의 ────────────────────────────────────────────────
class AgentState(TypedDict):
    """에이전트 그래프의 상태. messages는 Annotated로 누적됩니다."""

    messages: Annotated[list[BaseMessage], operator.add]


# ─── 노드 함수들 ──────────────────────────────────────────────
def create_graph_agent(model, tools, system_prompt: str = ""):
    """StateGraph 기반 ReAct 에이전트를 생성합니다.

    Args:
        model: LangChain ChatModel 인스턴스
        tools: 에이전트가 사용할 도구 리스트
        system_prompt: 시스템 프롬프트 문자열

    Returns:
        compiled StateGraph (invoke/ainvoke 가능)
    """
    # 모델에 도구 바인딩
    model_with_tools = model.bind_tools(tools)

    # 에이전트 노드: LLM이 다음 행동을 결정
    def agent_node(state: AgentState) -> dict:
        messages = state["messages"]
        if system_prompt:
            messages = [SystemMessage(content=system_prompt)] + messages
        response = model_with_tools.invoke(messages)
        return {"messages": [response]}

    # 도구 실행 노드
    tool_node = ToolNode(tools, handle_tool_errors=True)

    # 라우팅: 도구 호출이 있으면 tools로, 없으면 종료
    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    # ─── 그래프 구성 ──────────────────────────────────────────
    graph = StateGraph(AgentState)

    # 노드 추가
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    # 엣지 연결
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, ["tools", END])
    graph.add_edge("tools", "agent")  # 도구 실행 후 다시 에이전트로

    # 컴파일
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# ─── 확장 예시: 라우터 패턴 ───────────────────────────────────
# 아래는 질문 유형에 따라 다른 처리를 하는 고급 패턴 예시입니다.
# 필요에 따라 create_graph_agent를 수정하거나 새 함수를 만드세요.
#
# def create_router_agent(model, tools, system_prompt=""):
#     """질문 유형에 따라 다른 노드로 라우팅하는 에이전트"""
#
#     class RouterState(TypedDict):
#         messages: Annotated[list[BaseMessage], operator.add]
#         route: str  # "rag", "tool", "chat"
#
#     def classify(state: RouterState) -> dict:
#         """질문을 분류합니다."""
#         last_msg = state["messages"][-1].content
#         if "규정" in last_msg or "정책" in last_msg:
#             return {"route": "rag"}
#         elif "계산" in last_msg or "더해" in last_msg:
#             return {"route": "tool"}
#         return {"route": "chat"}
#
#     def route_query(state: RouterState) -> str:
#         return state["route"]
#
#     graph = StateGraph(RouterState)
#     graph.add_node("classify", classify)
#     graph.add_node("rag", rag_node)
#     graph.add_node("tool", tool_node)
#     graph.add_node("chat", chat_node)
#
#     graph.add_edge(START, "classify")
#     graph.add_conditional_edges("classify", route_query, ["rag", "tool", "chat"])
#     graph.add_edge("rag", END)
#     graph.add_edge("tool", END)
#     graph.add_edge("chat", END)
#
#     return graph.compile(checkpointer=MemorySaver())
