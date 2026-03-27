"""
사내 시스템 관리 도구 — systems.yaml 을 기반으로 시스템 검색 및 필터링 도구를 제공합니다.

사용 가능한 도구:
- search_systems        : 자연어로 시스템을 의미론적으로 검색합니다 (벡터 스토어)
- filter_by_sso         : SSO 연동 여부로 시스템 목록을 필터링합니다
- search_by_category    : 카테고리로 시스템 목록을 필터링합니다
- get_system_detail     : 시스템 이름으로 상세 정보와 접속 방법을 조회합니다
- get_onboarding_systems: 신규 입사자 필수 시스템 목록을 반환합니다
- add_system            : 새 시스템을 systems.yaml에 추가하고 즉시 반영합니다
- update_system         : 기존 시스템의 특정 필드를 수정하고 즉시 반영합니다
"""

import json
from pathlib import Path
from typing import Optional

import yaml
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

# ─── 데이터 로드 ─────────────────────────────────────────────
_DATA_PATH = Path(__file__).parent.parent / "mcp_servers" / "data" / "systems.yaml"

with open(_DATA_PATH, encoding="utf-8") as f:
    _systems: list[dict] = yaml.safe_load(f)["systems"]

# ─── 벡터 스토어 (모듈 로드 시 1회 구축) ─────────────────────
_vector_store: Optional[InMemoryVectorStore] = None


def _get_vector_store() -> InMemoryVectorStore:
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    from langchain_core.documents import Document

    docs = []
    for sys in _systems:
        content = (
            f"시스템명: {sys['name']}\n"
            f"카테고리: {sys.get('category', '')}\n"
            f"담당: {sys.get('owner', '')}\n"
            f"접근 범위: {sys.get('access_scope', '')}\n"
            f"설명: {sys.get('description', '').strip()}\n"
        )
        docs.append(Document(page_content=content, metadata={"name": sys["name"]}))

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    _vector_store = InMemoryVectorStore.from_documents(docs, embeddings)
    return _vector_store


def _format_system_brief(sys: dict) -> str:
    account_type = sys.get("account_type", "개인계정")
    account_label = "👤 개인계정" if account_type == "개인계정" else "👥 공용계정"
    return (
        f"• **{sys['name']}** ({sys.get('category', '')}) [{account_label}]\n"
        f"  - URL: {sys.get('url', 'N/A')} | 담당: {sys.get('owner', 'N/A')}"
    )


def _reset_cache():
    """시스템 목록과 벡터 스토어 캐시를 초기화합니다."""
    global _systems, _vector_store
    with open(_DATA_PATH, encoding="utf-8") as f:
        _systems = yaml.safe_load(f)["systems"]
    _vector_store = None


# ─── 도구 정의 ────────────────────────────────────────────────

@tool
def search_systems(query: str) -> str:
    """자연어 질문으로 사내 시스템을 의미론적으로 검색합니다.
    시스템 이름, 기능, 용도로 검색할 때 사용하세요.

    Args:
        query: 검색할 내용 (예: "회계 시스템", "협업 도구", "코드 관리")
    """
    vs = _get_vector_store()
    results = vs.similarity_search(query, k=3)
    if not results:
        return "검색 결과가 없습니다."

    lines = [f"'{query}' 검색 결과 ({len(results)}건):\n"]
    for doc in results:
        name = doc.metadata["name"]
        sys = next((s for s in _systems if s["name"] == name), None)
        if sys:
            lines.append(_format_system_brief(sys))
    return "\n".join(lines)


@tool
def filter_by_sso(sso: bool) -> str:
    """SSO(Single Sign-On) 연동 여부로 시스템 목록을 필터링합니다.

    Args:
        sso: True이면 SSO 연동 시스템, False이면 SSO 미연동(별도 로그인 필요) 시스템
    """
    filtered = [s for s in _systems if s.get("sso") == sso]
    if not filtered:
        return "해당 조건의 시스템이 없습니다."

    sso_label = "SSO 대상" if sso else "SSO 비대상"
    lines = [f"**{sso_label}** 시스템 목록 ({len(filtered)}건):\n"]
    for sys in filtered:
        lines.append(_format_system_brief(sys))
    return "\n".join(lines)


@tool
def search_by_category(category: str) -> str:
    """카테고리로 사내 시스템 목록을 조회합니다.
    카테고리: 업무, 협업, 교육, 보안, 개발, 인프라

    Args:
        category: 카테고리 이름 (예: "개발", "협업", "교육")
    """
    filtered = [s for s in _systems if category in s.get("category", "")]
    if not filtered:
        available = sorted({s.get("category", "") for s in _systems})
        return f"'{category}' 카테고리의 시스템이 없습니다. 사용 가능한 카테고리: {', '.join(available)}"

    lines = [f"**{category}** 카테고리 시스템 ({len(filtered)}건):\n"]
    for sys in filtered:
        lines.append(_format_system_brief(sys))
    return "\n".join(lines)


@tool
def get_system_detail(name: str) -> str:
    """시스템 이름으로 상세 정보와 접속 방법을 조회합니다.
    특정 시스템에 어떻게 접속하는지 안내할 때 사용하세요.

    Args:
        name: 시스템 이름 (예: "EP", "VDI", "Microsoft Teams", "이러닝")
    """
    # 정확한 이름 매칭 먼저 시도
    sys = next((s for s in _systems if s["name"].lower() == name.lower()), None)
    # 부분 일치로 재시도
    if not sys:
        sys = next((s for s in _systems if name.lower() in s["name"].lower()), None)
    if not sys:
        all_names = [s["name"] for s in _systems]
        return f"'{name}' 시스템을 찾을 수 없습니다. 등록된 시스템: {', '.join(all_names)}"

    detail = (
        f"## {sys['name']}\n\n"
        f"- **카테고리**: {sys.get('category', 'N/A')}\n"
        f"- **URL**: {sys.get('url', 'N/A')}\n"
        f"- **담당 부서**: {sys.get('owner', 'N/A')}\n"
        f"- **접근 범위**: {sys.get('access_scope', 'N/A')}\n"
        f"- **신규 입사자 필수**: {'예' if sys.get('onboarding_required') else '아니오'}\n\n"
        f"### 시스템 설명\n{sys.get('description', '').strip()}\n\n"
    )
    if sys.get("access_guide"):
        detail += f"### 접속 방법\n{sys['access_guide'].strip()}\n"
    return detail


@tool
def get_onboarding_systems() -> str:
    """신규 입사자가 반드시 등록해야 하는 시스템 목록을 반환합니다.
    온보딩, 신규 입사자 필수 시스템을 안내할 때 사용하세요.
    """
    required = [s for s in _systems if s.get("onboarding_required")]
    if not required:
        return "필수 온보딩 시스템 정보가 없습니다."

    lines = [f"**신규 입사자 필수 시스템** ({len(required)}건):\n"]
    for sys in required:
        lines.append(_format_system_brief(sys))
    lines.append("\n> 각 시스템의 접속 방법은 `get_system_detail` 도구로 확인하세요.")
    return "\n".join(lines)


@tool
def add_system(
    name: str,
    url: str,
    description: str,
    category: str = "업무",
    sso: bool = False,
    owner: str = "IT팀",
    access_scope: str = "사내",
    onboarding_required: bool = False,
    access_guide: str = "",
) -> str:
    """새 사내 시스템을 systems.yaml에 추가하고 즉시 검색에 반영합니다.
    사용자가 새 시스템을 등록하거나 추가해달라고 요청할 때 사용하세요.

    Args:
        name: 시스템 이름 (예: "인사포털")
        url: 접속 URL (예: "https://hr.company.com")
        description: 시스템 설명 (RAG 검색에 활용)
        category: 카테고리 — 업무/협업/교육/보안/개발/인프라 (기본: 업무)
        sso: SSO 연동 여부 (기본: False)
        owner: 담당 부서 (기본: IT팀)
        access_scope: 접근 범위 — 사내 / 사내·사외 (기본: 사내)
        onboarding_required: 신규 입사자 필수 여부 (기본: False)
        access_guide: 단계별 접속 방법 (생략 가능)
    """
    # 중복 확인
    if any(s["name"].lower() == name.lower() for s in _systems):
        return f"'{name}' 시스템이 이미 등록되어 있습니다. get_system_detail로 확인하세요."

    new_entry: dict = {
        "name": name,
        "sso": sso,
        "url": url,
        "category": category,
        "owner": owner,
        "onboarding_required": onboarding_required,
        "access_scope": access_scope,
        "description": description,
    }
    if access_guide:
        new_entry["access_guide"] = access_guide

    # yaml 파일 읽기 → 항목 추가 → 저장
    with open(_DATA_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data["systems"].append(new_entry)

    with open(_DATA_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    # 메모리 캐시 즉시 갱신
    _reset_cache()

    return (
        f"✅ '{name}' 시스템이 등록되었습니다.\n"
        f"- URL: {url}\n"
        f"- 카테고리: {category} | 담당: {owner}\n"
        f"- 전체 시스템 수: {len(_systems)}개"
    )


# 수정 가능한 필드 목록
_UPDATABLE_FIELDS = {
    "owner": "담당 부서",
    "url": "접속 URL",
    "category": "카테고리",
    "account_type": "계정 유형",
    "description": "시스템 설명",
    "access_guide": "접속 방법",
    "access_scope": "접근 범위",
    "onboarding_required": "신규 입사자 필수 여부",
}


@tool
def update_system(name: str, field: str, value: str) -> str:
    """기존 시스템의 특정 필드를 수정하고 즉시 반영합니다.
    담당 부서, URL, 접속 방법 등을 변경할 때 사용하세요.

    Args:
        name: 수정할 시스템 이름 (예: "EP", "Microsoft Teams")
        field: 수정할 필드명 — owner(담당부서) / url / category / description / access_guide / access_scope / onboarding_required
        value: 새로운 값 (예: "DX추진팀", "https://new.company.com")
    """
    if field not in _UPDATABLE_FIELDS:
        return (
            f"'{field}'은 수정할 수 없는 필드입니다.\n"
            f"수정 가능한 필드: {', '.join(_UPDATABLE_FIELDS.keys())}"
        )

    # yaml 파일 읽기
    with open(_DATA_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    sys_entry = next(
        (s for s in data["systems"] if s["name"].lower() == name.lower()), None
    )
    if not sys_entry:
        sys_entry = next(
            (s for s in data["systems"] if name.lower() in s["name"].lower()), None
        )
    if not sys_entry:
        all_names = [s["name"] for s in data["systems"]]
        return f"'{name}' 시스템을 찾을 수 없습니다. 등록된 시스템: {', '.join(all_names)}"

    # onboarding_required는 bool로 변환
    if field == "onboarding_required":
        parsed = value.strip().lower()
        if parsed in ("true", "yes", "예", "1"):
            value = True
        elif parsed in ("false", "no", "아니오", "0"):
            value = False
        else:
            return f"onboarding_required는 'true' 또는 'false'로 입력하세요."

    old_value = sys_entry.get(field, "(없음)")
    sys_entry[field] = value

    with open(_DATA_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    _reset_cache()

    field_label = _UPDATABLE_FIELDS[field]
    return (
        f"✅ '{sys_entry['name']}' 시스템의 {field_label}이(가) 수정되었습니다.\n"
        f"- 이전: {old_value}\n"
        f"- 변경: {value}"
    )
