# 나만의 AI 에이전트 만들기

6시간 동안 자신만의 AI 에이전트를 만들어봅니다.
기본 챗봇에서 시작하여, 단계별로 기능을 추가합니다.

## 빠른 시작 (5분)

```bash
# 1. 의존성 설치
uv sync

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 OPENAI_API_KEY를 입력하세요

# 3. 실행
uv run chainlit run app.py
```

브라우저에서 `http://localhost:8000` 접속 → 기본 챗봇이 동작합니다.

## 프로젝트 구조

```
base-agent/
├── app.py               # 웹 UI (수정 불필요)
├── agent.py              # ⭐ 에이전트 조립 (여기를 수정!)
│
├── prompts/              # Level 1: 프롬프트
│   ├── system.md         #   시스템 프롬프트
│   ├── AGENTS.md         #   에이전트 규칙
│   └── README.md         #   가이드 + 사례집
│
├── tools/                # Level 2A: 커스텀 도구
│   ├── example_tools.py  #   도구 예시 (@tool)
│   └── README.md         #   가이드
│
├── mcp_servers/          # Level 2B: MCP 서버
│   ├── math_server.py    #   서버 예시 (FastMCP)
│   └── README.md         #   가이드
│
├── rag/                  # Level 2C: RAG 검색
│   ├── retriever.py      #   벡터 검색 도구
│   ├── documents/        #   문서 폴더
│   └── README.md         #   가이드
│
├── skills/               # Level 2D: 스킬
│   ├── weekly-report/    #   스킬 예시 (SKILL.md)
│   └── README.md         #   가이드
│
└── graph/                # Level 3: 워크플로우
    ├── workflow.py        #   StateGraph 예시
    └── README.md          #   가이드
```

각 폴더의 `README.md`에 **쉬운 방법(추상화)**과 **직접 구현 방법**이 모두 설명되어 있습니다.

---

## Level 1: 프롬프트 엔지니어링 (1시간)

가장 쉽고 효과가 큰 커스터마이징입니다. 코드 수정 없이 텍스트만 바꾸면 됩니다.

### 1-1. 시스템 프롬프트 수정

`prompts/system.md`를 열고 에이전트의 역할과 규칙을 정의하세요.

```markdown
당신은 [역할]입니다.

## 규칙
- [규칙 1]
- [규칙 2]
- ...
```

> 참고: `prompts/README.md`에 10가지 이상의 프롬프트 패턴 사례집이 있습니다.

### 1-2. AGENTS.md 활성화 (선택)

항상 적용되는 규칙이 있다면 `prompts/AGENTS.md`를 수정하고,
`agent.py`에서 `memory=` 주석을 해제하세요.

```python
# agent.py
agent = create_deep_agent(
    ...
    memory=["./prompts/AGENTS.md"],  # 주석 해제
)
```

### 확인 방법
챗봇에게 역할이나 규칙에 관한 질문을 해보세요. 프롬프트대로 답변하는지 확인합니다.

---

## Level 2: 도구 연동 (2~3시간)

에이전트에게 **능력**을 부여합니다. 아래 4가지 중 원하는 것을 선택하세요.
여러 개를 동시에 연동할 수도 있습니다.

### 2A. 커스텀 도구 (tools/)

`tools/` 폴더에 `@tool` 함수를 추가합니다.

```python
# tools/my_tools.py (새 파일 생성)
from langchain_core.tools import tool

@tool
def search_web(query: str) -> str:
    """웹에서 정보를 검색합니다.

    Args:
        query: 검색할 내용
    """
    # TODO: 실제 검색 API 연동
    return f"'{query}'에 대한 검색 결과입니다."
```

파일명이 `_tools.py`로 끝나면 **자동 수집**됩니다. `agent.py` 수정 불필요!

> 상세 가이드: `tools/README.md`

### 2B. MCP 서버 (mcp_servers/)

외부 도구를 MCP 프로토콜로 연결합니다.

1. `mcp_servers/` 폴더에 서버 파일 추가
2. `agent.py`에서 MCP 섹션 주석 해제

```python
# agent.py — MCP 섹션 주석 해제
from langchain_mcp_adapters.client import MultiServerMCPClient

mcp_client = MultiServerMCPClient({
    "math": {
        "transport": "stdio",
        "command": "python",
        "args": ["mcp_servers/math_server.py"],
    },
})
mcp_tools = await mcp_client.get_tools()
tools += mcp_tools
```

> 상세 가이드: `mcp_servers/README.md`

### 2C. RAG 검색 (rag/)

문서를 기반으로 답변하는 기능을 추가합니다.

1. `rag/documents/` 폴더에 `.md` 문서 추가
2. `agent.py`에서 RAG 섹션 주석 해제

```python
# agent.py — RAG 섹션 주석 해제
from rag.retriever import get_rag_tools

tools += get_rag_tools()
```

> 상세 가이드: `rag/README.md`

### 2D. 스킬 (skills/)

에이전트에게 전문 지식을 부여합니다 (양식, 절차, 체크리스트 등).

1. `skills/my-skill/SKILL.md` 파일 생성
2. `agent.py`에서 스킬 섹션 주석 해제

```python
# agent.py — 스킬 섹션 주석 해제
skills = ["./skills/"]

agent = create_deep_agent(
    ...
    skills=skills,
    backend=FilesystemBackend(root_dir=".", virtual_mode=True),
)
```

> 상세 가이드: `skills/README.md`

---

## Level 3: 워크플로우 제어 (2시간, 도전)

`create_deep_agent`의 블랙박스를 벗어나, **StateGraph로 직접** 에이전트의 실행 흐름을 설계합니다.

### agent.py에서 교체

```python
# agent.py — Level 3
# create_deep_agent 대신:
from graph.workflow import create_graph_agent

agent = create_graph_agent(model, tools, system_prompt)
return agent
```

### 가능한 확장

| 패턴 | 설명 |
|------|------|
| ReAct 루프 | 기본 도구 사용 루프 (workflow.py에 구현됨) |
| 라우터 | 질문 유형별 다른 처리 파이프라인 |
| 다단계 파이프라인 | 검색 → 요약 → 검증 → 출력 |
| Orchestrator-Worker | 작업 분배 + 병렬 처리 |
| Human-in-the-Loop | 위험한 도구 실행 전 사용자 승인 |

> 상세 가이드: `graph/README.md`

---

## 과제 제출 안내

### 제출물
- GitHub 레포 링크 (또는 zip 파일)
- 간단한 시연 이미지 or 영상
- 최소 요구사항: Level 1 (프롬프트) + Level 2 중 1개 이상

### 평가 기준

| 항목 | 배점 |
|------|------|
| 에이전트 동작 여부 | 40% |
| 커스터마이징 수준 (프롬프트, 도구, 스킬 등) | 30% |
| 창의성 (아이디어, 활용 시나리오) | 20% |
| 발표 | 10% |

---

## 에이전트 아이디어

영감이 필요하다면 아래를 참고하세요:

| 에이전트 | 설명 | 주요 기술 |
|----------|------|----------|
| HR 어시스턴트 | 사내 규정 질문 답변 | RAG + 프롬프트 |
| 코드 리뷰어 | 코드 리뷰 + 개선 제안 | 스킬 + 프롬프트 |
| 회의록 작성기 | 회의 내용을 정리된 양식으로 | 스킬 + 프롬프트 |
| 데이터 분석가 | 계산 + 데이터 조회 | MCP + 커스텀 도구 |
| 풀스택 어시스턴트 | 규정 검색 + 계산 + 보고서 | RAG + MCP + 스킬 |
| 스마트 라우터 | 질문 유형별 자동 분기 | StateGraph |
