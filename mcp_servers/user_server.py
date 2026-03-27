"""
MCP User Store Server (Stdio 전송)

users.yaml 파일의 읽기/쓰기를 담당하는 MCP 서버입니다.
user_tools.py가 이 서버를 통해 사용자 데이터에 접근합니다.

제공 도구:
  - load_users()              : users.yaml 전체 사용자 목록을 JSON 문자열로 반환
  - save_users(users_json)    : 사용자 목록(JSON 문자열)을 users.yaml에 저장
  - find_user(user_id)        : 특정 사용자 정보를 JSON 문자열로 반환 (없으면 빈 문자열)
"""

import json
from pathlib import Path

import yaml
from fastmcp import FastMCP

mcp = FastMCP("UserStore")

_DATA_PATH = Path(__file__).parent.parent / "data" / "users.yaml"


def _read_yaml() -> list[dict]:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f).get("users") or []


def _write_yaml(users: list[dict]) -> None:
    with open(_DATA_PATH, "w", encoding="utf-8") as f:
        yaml.dump(
            {"users": users},
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )


@mcp.tool()
def load_users() -> str:
    """users.yaml의 전체 사용자 목록을 JSON 문자열로 반환합니다."""
    users = _read_yaml()
    return json.dumps(users, ensure_ascii=False)


@mcp.tool()
def save_users(users_json: str) -> str:
    """사용자 목록(JSON 문자열)을 users.yaml에 저장합니다.

    Args:
        users_json: 저장할 사용자 목록 JSON 문자열
    """
    users = json.loads(users_json)
    _write_yaml(users)
    return f"저장 완료: {len(users)}명"


@mcp.tool()
def find_user(user_id: str) -> str:
    """EP ID로 특정 사용자 정보를 JSON 문자열로 반환합니다. 없으면 빈 문자열 반환.

    Args:
        user_id: 조회할 EP ID
    """
    users = _read_yaml()
    user = next((u for u in users if u["id"].lower() == user_id.lower()), None)
    return json.dumps(user, ensure_ascii=False) if user else ""


if __name__ == "__main__":
    mcp.run(transport="stdio")
