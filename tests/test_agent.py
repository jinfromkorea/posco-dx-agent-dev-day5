"""
base-agent 프레임워크 검증 테스트

각 Level의 핵심 기능이 정상 동작하는지 검증합니다.
실행: uv run python tests/test_agent.py
"""

import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 + 작업 디렉토리 변경
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

PASS = 0
FAIL = 0


def report(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    status = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


# ═══════════════════════════════════════════════════════════════
# 1. 기본 import 검증
# ═══════════════════════════════════════════════════════════════
print("\n=== 1. Import 검증 ===")

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
    report("dotenv", True)
except Exception as e:
    report("dotenv", False, str(e))

try:
    from langchain_openai import ChatOpenAI

    report("langchain_openai", True)
except Exception as e:
    report("langchain_openai", False, str(e))

try:
    from deepagents import create_deep_agent

    report("deepagents", True)
except Exception as e:
    report("deepagents", False, str(e))

try:
    from langgraph.graph import StateGraph

    report("langgraph", True)
except Exception as e:
    report("langgraph", False, str(e))

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    report("langchain_mcp_adapters", True)
except Exception as e:
    report("langchain_mcp_adapters", False, str(e))

try:
    from fastmcp import FastMCP

    report("fastmcp", True)
except Exception as e:
    report("fastmcp", False, str(e))

try:
    import chainlit

    report("chainlit", True)
except Exception as e:
    report("chainlit", False, str(e))


# ═══════════════════════════════════════════════════════════════
# 2. Level 1: 프롬프트 로딩 검증
# ═══════════════════════════════════════════════════════════════
print("\n=== 2. Level 1: 프롬프트 ===")

system_md = Path(__file__).parent.parent / "prompts" / "system.md"
report("prompts/system.md 존재", system_md.exists())

if system_md.exists():
    content = system_md.read_text(encoding="utf-8")
    report("system.md 내용 있음", len(content) > 10, f"{len(content)}자")

agents_md = Path(__file__).parent.parent / "prompts" / "AGENTS.md"
report("prompts/AGENTS.md 존재", agents_md.exists())


# ═══════════════════════════════════════════════════════════════
# 3. Level 2A: 도구 자동 수집 검증
# ═══════════════════════════════════════════════════════════════
print("\n=== 3. Level 2A: 커스텀 도구 ===")

try:
    from tools import all_tools

    report("tools.all_tools import", True, f"{len(all_tools)}개 도구")

    tool_names = [t.name for t in all_tools]
    report("get_current_time 도구 존재", "get_current_time" in tool_names, str(tool_names))

    # 도구 실행 테스트
    time_tool = next((t for t in all_tools if t.name == "get_current_time"), None)
    if time_tool:
        result = time_tool.invoke({})
        report("get_current_time 실행", "년" in result, result)
    else:
        report("get_current_time 실행", False, "도구를 찾을 수 없음")
except Exception as e:
    report("tools.all_tools import", False, str(e))


# ═══════════════════════════════════════════════════════════════
# 4. Level 2B: MCP 서버 검증
# ═══════════════════════════════════════════════════════════════
print("\n=== 4. Level 2B: MCP 서버 ===")

mcp_file = Path(__file__).parent.parent / "mcp_servers" / "math_server.py"
report("math_server.py 존재", mcp_file.exists())


async def test_mcp():
    try:
        client = MultiServerMCPClient(
            {
                "math": {
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": [str(mcp_file)],
                },
            }
        )
        tools = await client.get_tools()
        tool_names = [t.name for t in tools]
        report("MCP 도구 로드", len(tools) >= 2, str(tool_names))
        report("add 도구 존재", "add" in tool_names)
        report("multiply 도구 존재", "multiply" in tool_names)

        # 도구 실행 테스트
        add_tool = next(t for t in tools if t.name == "add")
        result = await add_tool.ainvoke({"a": 3, "b": 7})
        report("MCP add(3,7) 실행", "10" in str(result), str(result))
    except Exception as e:
        report("MCP 서버 연결", False, str(e))


asyncio.run(test_mcp())


# ═══════════════════════════════════════════════════════════════
# 5. Level 2C: RAG 검증
# ═══════════════════════════════════════════════════════════════
print("\n=== 5. Level 2C: RAG ===")

docs_dir = Path(__file__).parent.parent / "rag" / "documents"
report("rag/documents/ 존재", docs_dir.exists())

md_files = list(docs_dir.glob("*.md"))
report("문서 파일 존재", len(md_files) > 0, f"{len(md_files)}개 파일")

try:
    import os

    if os.environ.get("OPENAI_API_KEY"):
        from rag.retriever import get_rag_tools

        rag_tools = get_rag_tools()
        report("RAG 도구 로드", len(rag_tools) > 0, f"{len(rag_tools)}개 도구")

        retrieve_tool = rag_tools[0]
        result = retrieve_tool.invoke("연차 규정")
        report("RAG 검색 '연차 규정'", "연차" in str(result), f"{len(str(result))}자")

        result2 = retrieve_tool.invoke("출장비")
        report("RAG 검색 '출장비'", "출장" in str(result2), f"{len(str(result2))}자")
    else:
        report("RAG 도구 로드", False, "OPENAI_API_KEY 미설정 — 스킵")
except Exception as e:
    report("RAG 도구", False, str(e))


# ═══════════════════════════════════════════════════════════════
# 6. Level 2D: 스킬 검증
# ═══════════════════════════════════════════════════════════════
print("\n=== 6. Level 2D: 스킬 ===")

skill_file = Path(__file__).parent.parent / "skills" / "weekly-report" / "SKILL.md"
report("SKILL.md 존재", skill_file.exists())

if skill_file.exists():
    content = skill_file.read_text(encoding="utf-8")
    report("YAML 프론트매터 있음", content.startswith("---"))
    report("name 필드 있음", "name:" in content)
    report("description 필드 있음", "description:" in content)


# ═══════════════════════════════════════════════════════════════
# 7. Level 3: StateGraph 검증
# ═══════════════════════════════════════════════════════════════
print("\n=== 7. Level 3: StateGraph ===")

try:
    from graph.workflow import create_graph_agent

    report("create_graph_agent import", True)
except Exception as e:
    report("create_graph_agent import", False, str(e))


# ═══════════════════════════════════════════════════════════════
# 8. 에이전트 통합 테스트 (API 키 필요)
# ═══════════════════════════════════════════════════════════════
print("\n=== 8. 에이전트 통합 테스트 ===")


async def test_agent_integration():
    import os

    if not os.environ.get("OPENAI_API_KEY"):
        report("통합 테스트", False, "OPENAI_API_KEY 미설정 — 스킵")
        return

    try:
        from agent import create_base_agent

        agent = await create_base_agent()
        report("에이전트 생성", True)

        # 기본 대화 테스트
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "안녕하세요! 오늘 날짜를 알려주세요."}]},
            config={"configurable": {"thread_id": "test-1"}},
        )
        answer = result["messages"][-1].content
        report("기본 대화", len(answer) > 5, f"{answer[:80]}...")

        # 도구 호출 테스트 (get_current_time)
        result2 = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "지금 정확한 시간이 몇 시인지 도구를 사용해서 알려줘."}]},
            config={"configurable": {"thread_id": "test-2"}},
        )
        answer2 = result2["messages"][-1].content
        has_time = any(kw in answer2 for kw in ["시", "분", ":", "년"])
        report("도구 호출 (시간)", has_time, f"{answer2[:80]}...")

    except Exception as e:
        report("통합 테스트", False, str(e))


asyncio.run(test_agent_integration())


# ═══════════════════════════════════════════════════════════════
# 결과 요약
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"결과: {PASS} PASS / {FAIL} FAIL (총 {PASS+FAIL}건)")
print(f"{'='*50}")

if FAIL > 0:
    sys.exit(1)
