"""
사용자 관리 도구 — user_server MCP를 통해 users.yaml을 읽고 씁니다.

MCP 클라이언트는 agent.py에서 시작하여 init_user_client()로 주입합니다.
모든 @tool 함수는 async def로 정의되어 있습니다.

사용 가능한 도구:
- set_current_user      : 현재 세션의 사용자를 설정합니다 ("나는 john이야")
- get_my_systems        : 내가 접근 가능한 시스템 목록을 반환합니다
- add_user              : 새 사용자를 등록합니다
- grant_system_access   : 특정 사용자에게 시스템 접근 권한을 부여합니다
- revoke_system_access  : 특정 사용자의 시스템 접근 권한을 취소합니다
"""

import json
from pathlib import Path
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

# ─ agent.py가 주입한 MCP 클라이언트 ──────────────────────────
_user_client = None
_USER_SERVER = str(Path(__file__).parent.parent / "mcp_servers" / "user_server.py")


def init_user_client(client) -> None:
    """agent.py에서 MCP 클라이언트를 주입합니다."""
    global _user_client
    _user_client = client


# ─ async MCP 헬퍼 ────────────────────────────────────────────

async def _call_mcp(name: str, args: dict):
    """MCP 도구를 호출합니다. 클라이언트가 주입되지 않은 경우 subprocess로 폴백."""
    if _user_client is not None:
        return await _user_client.call_tool(name, args)
    from fastmcp import Client
    async with Client(_USER_SERVER) as client:
        return await client.call_tool(name, args)


async def _load_users() -> list[dict]:
    result = await _call_mcp("load_users", {})
    return json.loads(result.content[0].text)


async def _save_users(users: list[dict]) -> None:
    await _call_mcp("save_users", {"users_json": json.dumps(users, ensure_ascii=False)})


async def _find_user(user_id: str) -> Optional[dict]:
    result = await _call_mcp("find_user", {"user_id": user_id})
    text = result.content[0].text
    return json.loads(text) if text else None


# ─── 세션별 현재 사용자 추적 ─────────────────────────────────
# thread_id → user_id 매핑 (프로세스 내 메모리)
_session_users: dict[str, str] = {}


def _get_system_map(user: dict) -> dict:
    """systems 필드를 {'업무용': [...], '개인용': [{name, account}, ...]} 형태로 반환합니다.
    하위 호환: 기존 리스트 형식이면 전부 업무용으로 처리합니다."""
    systems = user.get("systems", [])
    if isinstance(systems, dict):
        return {"업무용": systems.get("업무용") or [], "개인용": systems.get("개인용") or []}
    return {"업무용": list(systems), "개인용": []}


def _personal_name(entry) -> str:
    """'개인용' 항목에서 시스템 이름을 반환합니다."""
    return entry["name"] if isinstance(entry, dict) else entry


# ─── 도구 정의 ────────────────────────────────────────────────

@tool
async def set_current_user(user_id: str, config: RunnableConfig) -> str:
    """현재 세션의 사용자를 설정합니다. "나는 john이야", "내 ID는 jane" 같은 요청에 사용하세요.

    Args:
        user_id: EP ID (예: john, jane, newbie)
    """
    thread_id = config.get("configurable", {}).get("thread_id", "default")

    user = await _find_user(user_id)
    if not user:
        users = await _load_users()
        available = [u["id"] for u in users]
        return (
            f"'{user_id}' 사용자를 찾을 수 없습니다.\n"
            f"등록된 사용자: {', '.join(available)}\n"
            f"새 사용자 등록은 add_user 도구를 사용하세요."
        )

    _session_users[thread_id] = user_id
    sys_map = _get_system_map(user)
    total = len(sys_map["업무용"]) + len(sys_map["개인용"])
    return (
        f"✅ 로그인 완료!\n"
        f"- 이름: {user['name']} ({user['id']})\n"
        f"- 접근 가능 시스템: {total}개 (업무용 {len(sys_map['업무용'])}개, 개인용 {len(sys_map['개인용'])}개)"
    )


@tool
async def get_my_systems(config: RunnableConfig) -> str:
    """내가 접근 가능한 시스템 목록과 각 시스템의 접속 방법을 반환합니다.
    "내가 쓸 수 있는 시스템", "내 시스템 목록" 요청에 사용하세요.
    """
    from tools.system_tools import _systems, _format_system_brief

    thread_id = config.get("configurable", {}).get("thread_id", "default")
    user_id = _session_users.get(thread_id)

    if not user_id:
        return (
            "로그인된 사용자가 없습니다.\n"
            "'나는 [EP ID]야'라고 먼저 알려주세요."
        )

    user = await _find_user(user_id)
    if not user:
        return "사용자 정보를 찾을 수 없습니다."

    sys_map = _get_system_map(user)
    total = len(sys_map["업무용"]) + len(sys_map["개인용"])
    if total == 0:
        return f"{user['name']}님은 아직 접근 권한이 있는 시스템이 없습니다."

    lines = [f"**{user['name']}님의 접근 가능 시스템** ({total}개):\n"]

    # 업무용: 시스템명 문자열 리스트
    if sys_map["업무용"]:
        lines.append("\n**[업무용]** (EP SSO 통합 로그인)")
        for name in sys_map["업무용"]:
            sys_info = next((s for s in _systems if s["name"] == name), None)
            if sys_info:
                lines.append(_format_system_brief(sys_info))
            else:
                lines.append(f"• **{name}** (시스템 정보 없음)")

    # 개인용: {name, account} 객체 리스트
    if sys_map["개인용"]:
        lines.append("\n**[개인용]** (별도 계정 사용)")
        for entry in sys_map["개인용"]:
            name = _personal_name(entry)
            account = entry.get("account", "") if isinstance(entry, dict) else ""
            sys_info = next((s for s in _systems if s["name"] == name), None)
            brief = _format_system_brief(sys_info) if sys_info else f"• **{name}**"
            lines.append(brief + (f" | 계정: `{account}`" if account else ""))

    lines.append("\n> 특정 시스템의 접속 방법은 get_system_detail 도구로 확인하세요.")
    return "\n".join(lines)


@tool
async def add_user(
    user_id: str,
    name: str,
    systems: str = "",
) -> str:
    """새 사용자를 users.yaml에 등록합니다.

    Args:
        user_id: EP ID (예: hong123)
        name: 이름 (예: 홍길동)
        systems: 접근 가능한 시스템 이름 목록, 쉼표로 구분 (예: "EP, Microsoft Teams")
    """
    users = await _load_users()
    if any(u["id"].lower() == user_id.lower() for u in users):
        return f"'{user_id}' ID는 이미 등록되어 있습니다."

    system_list = [s.strip() for s in systems.split(",") if s.strip()] if systems else []

    # onboarding_required: true 인 시스템을 기본으로 추가
    from tools.system_tools import _systems as all_systems
    onboarding_defaults = [s["name"] for s in all_systems if s.get("onboarding_required")]
    for sys_name in onboarding_defaults:
        if sys_name not in system_list:
            system_list.append(sys_name)

    # EP는 항상 맨 앞에
    if "EP" in system_list:
        system_list.remove("EP")
    system_list.insert(0, "EP")

    new_user = {
        "id": user_id,
        "name": name,
        "systems": {
            "업무용": system_list,
            "개인용": [],
        },
    }
    users.append(new_user)
    await _save_users(users)

    return (
        f"✅ '{name}' ({user_id}) 사용자가 등록되었습니다.\n"
        f"- 초기 접근 시스템: {', '.join(system_list) if system_list else '없음'}"
    )


@tool
async def grant_system_access(user_id: str, system_name: str, use_type: str = "업무용", account: str = "") -> str:
    """특정 사용자에게 시스템 접근 권한을 부여합니다.

    Args:
        user_id: EP ID
        system_name: 시스템 이름 (systems.yaml의 name과 일치해야 함)
        use_type: 업무용 또는 개인용 (기본: 업무용)
        account: 개인용 시 사용하는 계정명 (업무용일 경우 생럵 가능)
    """
    from tools.system_tools import _systems

    # 시스템 존재 확인
    sys_info = next((s for s in _systems if s["name"].lower() == system_name.lower()), None)
    if not sys_info:
        # 부분 일치 시도
        sys_info = next((s for s in _systems if system_name.lower() in s["name"].lower()), None)
    if not sys_info:
        return f"'{system_name}' 시스템을 찾을 수 없습니다. search_systems로 정확한 이름을 확인하세요."

    actual_name = sys_info["name"]
    users = await _load_users()
    user = next((u for u in users if u["id"].lower() == user_id.lower()), None)
    if not user:
        return f"'{user_id}' 사용자를 찾을 수 없습니다."

    sys_map = _get_system_map(user)
    all_names = [n for n in sys_map["업무용"]] + [_personal_name(e) for e in sys_map["개인용"]]
    if actual_name in all_names:
        return f"'{user['name']}' 님은 이미 '{actual_name}' 시스템에 접근 권한이 있습니다."

    if use_type not in ("업무용", "개인용"):
        use_type = "업무용"

    if use_type == "개인용":
        entry = {"name": actual_name, "account": account} if account else {"name": actual_name}
        sys_map["개인용"].append(entry)
    else:
        sys_map["업무용"].append(actual_name)

    user["systems"] = sys_map
    await _save_users(users)

    detail = f" (account: {account})" if account else ""
    return f"✅ '{user['name']}' ({user_id}) 님에게 '{actual_name}' 접근 권한이 부여되었습니다. ({use_type}{detail})"


@tool
async def revoke_system_access(user_id: str, system_name: str) -> str:
    """특정 사용자의 시스템 접근 권한을 취소합니다.

    Args:
        user_id: EP ID
        system_name: 취소할 시스템 이름
    """
    users = await _load_users()
    user = next((u for u in users if u["id"].lower() == user_id.lower()), None)
    if not user:
        return f"'{user_id}' 사용자를 찾을 수 없습니다."

    sys_map = _get_system_map(user)
    matched = None
    matched_type = None
    # 업무용: 문자열 리스트
    found_biz = next((s for s in sys_map["업무용"] if system_name.lower() in s.lower()), None)
    if found_biz:
        matched, matched_type = found_biz, "업무용"
    else:
        # 개인용: {name, account} 객체 리스트
        found_personal = next((e for e in sys_map["개인용"] if system_name.lower() in _personal_name(e).lower()), None)
        if found_personal:
            matched, matched_type = found_personal, "개인용"

    if not matched:
        return f"'{user['name']}' 님은 '{system_name}' 시스템 권한이 없습니다."

    sys_map[matched_type].remove(matched)
    user["systems"] = sys_map
    await _save_users(users)

    removed_name = _personal_name(matched) if matched_type == "개인용" else matched
    return f"✅ '{user['name']}' ({user_id}) 님의 '{removed_name}' 접근 권한이 취소되었습니다."
