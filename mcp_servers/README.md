# mcp_servers/ — MCP 서버

Model Context Protocol(MCP) 서버를 정의합니다.
MCP는 에이전트가 외부 도구/서비스를 표준 프로토콜로 호출하는 방식입니다.

## 쉬운 방법 (추상화)

### 1단계: FastMCP로 서버 작성

```python
# mcp_servers/my_server.py
from fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool()
def hello(name: str) -> str:
    """이름을 받아 인사합니다."""
    return f"안녕하세요, {name}!"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 2단계: agent.py에서 연결

`agent.py`의 MCP 섹션 주석을 해제하고, 서버 경로를 추가합니다.

```python
mcp_client = MultiServerMCPClient(
    {
        "math": {
            "transport": "stdio",
            "command": "python",
            "args": ["mcp_servers/math_server.py"],
        },
        # 새 서버 추가
        "my_server": {
            "transport": "stdio",
            "command": "python",
            "args": ["mcp_servers/my_server.py"],
        },
    }
)
mcp_tools = await mcp_client.get_tools()
tools += mcp_tools
```

### 전송 방식

| 방식 | 설정 | 사용 시나리오 |
|------|------|-------------|
| **stdio** | `transport: "stdio"` | 로컬 서버, 서브프로세스로 자동 시작 |
| **streamable-http** | `transport: "streamable_http"`, `url: "http://..."` | 원격 서버, 별도 프로세스로 미리 시작 필요 |

## 직접 구현

### low-level MCP 서버 (`mcp` 라이브러리)

FastMCP 대신 `mcp` 라이브러리로 더 세밀한 제어가 가능합니다.

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("MyServer")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="search",
            description="검색합니다",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색어"}
                },
                "required": ["query"],
            },
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search":
        return [TextContent(type="text", text=f"결과: {arguments['query']}")]
```

### 외부 MCP 서버 연결 (npx 등)

npm으로 배포된 MCP 서버를 연결할 수도 있습니다.

```python
mcp_client = MultiServerMCPClient(
    {
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"],
        },
    }
)
```

### Streamable HTTP 서버 (원격)

별도 프로세스로 서버를 시작하고 HTTP로 연결합니다.

```python
# 서버 시작: python my_server.py (포트 8000)
# FastMCP에서 transport="streamable-http" 지정
mcp = FastMCP("RemoteServer")

@mcp.tool()
def remote_tool(input: str) -> str:
    """원격 도구"""
    return f"처리 완료: {input}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8000)
```

```python
# agent.py에서 연결
mcp_client = MultiServerMCPClient(
    {
        "remote": {
            "transport": "streamable_http",
            "url": "http://localhost:8000/mcp",
        },
    }
)
```

## MCP 서버 아이디어

| 서버 | 설명 | 난이도 |
|------|------|--------|
| 계산기 | 사칙연산 (예시 제공됨) | 쉬움 |
| 날씨 | 외부 날씨 API 래핑 | 보통 |
| DB 쿼리 | SQLite 조회/삽입 | 보통 |
| 파일 관리 | 파일 읽기/쓰기/검색 | 보통 |
| GitHub | 이슈/PR 관리 | 어려움 |
