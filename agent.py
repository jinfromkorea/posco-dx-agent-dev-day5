"""
에이전트 조립 파일 — ⭐ 이 파일을 수정하여 에이전트를 커스터마이징하세요.

주석을 해제하면 각 기능이 활성화됩니다:
- Level 1: 프롬프트 수정 (prompts/)
- Level 2: 도구 연동 (tools/, mcp_servers/, rag/, skills/)
- Level 3: 워크플로우 제어 (graph/)
"""

import sys
from pathlib import Path

# Chainlit 실행 시 tools 패키지를 찾을 수 있도록 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from deepagents import create_deep_agent

load_dotenv(override=True)

# ─── 모델 설정 ───────────────────────────────────────────────
model = ChatOpenAI(model="gpt-5.4-mini")
# model = ChatOpenAI(model="gpt-5.4")              # 더 강력한 모델
# from langchain_anthropic import ChatAnthropic
# model = ChatAnthropic(model="claude-sonnet-4-5-20250929")


def _load_prompt(path: str) -> str:
    """마크다운 파일에서 프롬프트를 로드합니다."""
    file = Path(__file__).parent / path
    if file.exists():
        return file.read_text(encoding="utf-8")
    return "당신은 도움이 되는 AI 어시스턴트입니다. 한국어로 답변하세요."


async def create_base_agent():
    """에이전트를 생성합니다. 주석을 해제하여 기능을 추가하세요."""

    # ─── Level 1: 프롬프트 ────────────────────────────────────
    # prompts/system.md 파일을 수정하여 에이전트의 성격과 규칙을 정의하세요.
    system_prompt = _load_prompt("prompts/system.md")

    # ─── Level 2A: 커스텀 도구 ────────────────────────────────
    # tools/example_tools.py에 @tool 함수를 추가하세요.
    from tools import all_tools

    tools = [*all_tools]

    # ─── Level 2B: MCP 서버 도구 ──────────────────────────────
    # user_server를 시작하고 user_tools에 클라이언트를 주입합니다.
    from fastmcp import Client
    from tools.user_tools import init_user_client

    user_mcp_client = Client("mcp_servers/user_server.py")
    await user_mcp_client.__aenter__()
    init_user_client(user_mcp_client)

    # ─── Level 2C: RAG 검색 도구 ────────────────────────────────
    # systems.yaml의 description/access_guide + documents/ 문서를 벡터 검색
    from rag.retriever import get_rag_tools
    tools += get_rag_tools()

    # ─── Level 2D: 스킬 ──────────────────────────────────────
    # skills/ 폴더의 SKILL.md를 에이전트에 주입합니다.
    skills = ["./skills/"]

    # ─── 에이전트 생성 ────────────────────────────────────────
    checkpointer = MemorySaver()

    agent = create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        # ─── Level 1: AGENTS.md 규칙 주입 ─────────────────────
        memory=["./prompts/AGENTS.md"],
        # ─── Level 2D: 스킬 활성화 ────────────────────────────
        skills=skills,
    )

    return agent

    # ─── Level 3: StateGraph로 대체 (도전) ────────────────────
    # create_deep_agent 대신 직접 그래프를 구성하려면:
    #
    # from graph.workflow import create_graph_agent
    # agent = create_graph_agent(model, tools, system_prompt)
    # return agent
