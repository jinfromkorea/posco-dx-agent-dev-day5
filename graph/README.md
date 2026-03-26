# graph/ — StateGraph 워크플로우

에이전트의 실행 흐름을 직접 제어합니다.
`create_deep_agent`의 블랙박스를 벗어나, 노드/엣지/조건부 라우팅을 직접 구성합니다.

## 쉬운 방법 (추상화)

`create_deep_agent`를 그대로 사용하면 됩니다 (agent.py 기본값).
내부적으로 이미 StateGraph 기반으로 동작합니다.

```python
# agent.py (기본값 — 수정 불필요)
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=model,
    tools=tools,
    system_prompt=system_prompt,
)
```

## 직접 구현

### 1단계: workflow.py 이해

`graph/workflow.py`에 ReAct 패턴 에이전트가 구현되어 있습니다.

```
[START] → [agent] → 도구 호출? → Yes → [tools] → [agent] (반복)
                          └── No → [END]
```

### 2단계: agent.py에서 교체

```python
# agent.py에서 create_deep_agent 대신:
from graph.workflow import create_graph_agent

agent = create_graph_agent(model, tools, system_prompt)
return agent
```

### 핵심 개념

| 개념 | 설명 |
|------|------|
| **StateGraph** | 상태를 가진 방향 그래프. 노드와 엣지로 구성 |
| **Node** | 상태를 받아서 상태 업데이트를 반환하는 함수 |
| **Edge** | 노드 간 실행 순서. 정적(add_edge) 또는 동적(add_conditional_edges) |
| **State** | 그래프 전체에서 공유되는 데이터. Annotated로 누적 전략 지정 |
| **compile()** | 그래프를 실행 가능한 형태로 변환 |

### 패턴 1: 기본 ReAct 루프 (workflow.py에 구현됨)

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)      # LLM이 다음 행동 결정
graph.add_node("tools", ToolNode(tools)) # 도구 실행
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, ["tools", END])
graph.add_edge("tools", "agent")         # 도구 → 다시 에이전트
compiled = graph.compile()
```

### 패턴 2: 라우터 노드

질문 유형에 따라 다른 처리 파이프라인으로 분기합니다.

```python
def classify(state) -> dict:
    """질문 유형을 분류합니다."""
    msg = state["messages"][-1].content
    if "규정" in msg:
        return {"route": "rag"}
    elif "계산" in msg:
        return {"route": "calc"}
    return {"route": "chat"}

graph = StateGraph(State)
graph.add_node("classify", classify)
graph.add_node("rag", rag_handler)
graph.add_node("calc", calc_handler)
graph.add_node("chat", chat_handler)

graph.add_edge(START, "classify")
graph.add_conditional_edges("classify", lambda s: s["route"], ["rag", "calc", "chat"])
graph.add_edge("rag", END)
graph.add_edge("calc", END)
graph.add_edge("chat", END)
```

### 패턴 3: 다단계 파이프라인

```
[검색] → [요약] → [검증] → [출력]
```

```python
graph = StateGraph(State)
graph.add_node("search", search_node)
graph.add_node("summarize", summarize_node)
graph.add_node("verify", verify_node)
graph.add_node("output", output_node)

graph.add_edge(START, "search")
graph.add_edge("search", "summarize")
graph.add_edge("summarize", "verify")
graph.add_conditional_edges("verify", check_quality, ["search", "output"])  # 품질 낮으면 재검색
graph.add_edge("output", END)
```

### 패턴 4: Command로 상태 + 라우팅 동시 처리

```python
from langgraph.types import Command
from typing import Literal

def smart_node(state) -> Command[Literal["node_a", "node_b"]]:
    """상태를 업데이트하면서 동시에 다음 노드를 결정합니다."""
    if state["count"] > 5:
        return Command(update={"status": "done"}, goto="node_b")
    return Command(update={"count": state["count"] + 1}, goto="node_a")
```

### 패턴 5: Orchestrator-Worker (병렬 처리)

```python
from langgraph.types import Send

def orchestrator(state):
    """작업을 분배하여 병렬 실행합니다."""
    return [Send("worker", {"task": t}) for t in state["tasks"]]

graph = StateGraph(State)
graph.add_node("worker", worker_node)
graph.add_node("synthesize", synthesize_node)
graph.add_conditional_edges(START, orchestrator, ["worker"])
graph.add_edge("worker", "synthesize")
graph.add_edge("synthesize", END)
```

## 주의사항

- `compile()` 호출 전에는 `invoke()` 불가
- 노드 함수는 **상태 전체를 반환하지 말고, 변경된 부분만** 딕셔너리로 반환
- 리스트 필드에 `Annotated[list, operator.add]` 없으면 마지막 값만 남음
- `add_edge`와 `Command(goto=...)`를 같은 노드에 동시 사용하면 **둘 다 실행됨**
