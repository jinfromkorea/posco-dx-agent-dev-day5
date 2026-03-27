---
marp: true
theme: default
paginate: true
backgroundColor: #ffffff
style: |
  section {
    font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif;
    font-size: 1.1rem;
  }
  h1 { color: #1a3a5c; border-bottom: 3px solid #2e86de; padding-bottom: 0.3em; }
  h2 { color: #2e86de; }
  h3 { color: #444; }
  table { width: 100%; font-size: 0.85rem; }
  th { background: #2e86de; color: white; }
  tr:nth-child(even) { background: #f0f4f8; }
  code { background: #f0f4f8; padding: 2px 6px; border-radius: 4px; }
  section.title {
    background: linear-gradient(135deg, #1a3a5c 0%, #2e86de 100%);
    color: white;
  }
  section.title h1 { color: white; border-bottom: 2px solid rgba(255,255,255,0.4); }
  section.title h2 { color: #cfe2f3; }
  section.title p { color: #cfe2f3; }
---

<!-- _class: title -->

# 사내 시스템 안내 AI 에이전트

## posco-dx-agent-dev-day5 프로젝트 보고서

2026년 3월 27일

---

# 프로젝트 개요

> 직원들이 사내 시스템에 대해 자연어로 질문하면
> 접속 방법·계정·인증 수단을 정확하게 안내하는 AI 어시스턴트

### 출발점 — 직원이 헷갈리는 것들

- 사내 시스템 로그인 계정이 개인계정인가, 공용계정인가?
- EP ID 기반 SSO가 적용되는 시스템은 어디인가?
- 로그인 시 추가 인증(OTP)이 필요한가?
- 사내 시스템 접근 수단은 무엇인가? (브라우저, VDI, IDE 플러그인…)
- 업무 외 개인적으로 사용하는 외부 사이트는 어떻게 접속하나?

---

# 기술 스택

| 분류 | 기술 |
|------|------|
| AI 프레임워크 | LangChain + LangGraph + DeepAgents |
| LLM | OpenAI GPT-5.4-mini |
| 웹 UI | Chainlit 2.5.0 |
| 도구 프로토콜 | FastMCP 3.1.1 |
| 임베딩·RAG | OpenAI text-embedding-3-small + InMemoryVectorStore |
| 모니터링 | Langfuse |
| 패키지 관리 | uv / pyproject.toml (Python 3.12+) |

---

# 아키텍처 — 레이어별 구조

```
app.py  (Chainlit 웹 UI)
  └─► agent.py  (에이전트 조립 ★)
        │
        ├─ Level 1  prompts/       시스템 프롬프트
        ├─ Level 2A tools/         커스텀 도구 (12개)
        ├─ Level 2B mcp_servers/   MCP 서버 (2개)
        ├─ Level 2C rag/           벡터 검색 (3개 문서)
        ├─ Level 2D skills/        전문 지식 (2개 스킬)
        └─ Level 3  graph/         StateGraph 워크플로우
```

**상태 관리**: MemorySaver (대화 세션 내 유지)
**관찰성**: Langfuse 콜백으로 모든 LLM 호출 추적

---

# 도구 목록 — 커스텀 도구 (tools/)

| 파일 | 도구명 | 기능 |
|------|--------|------|
| system_tools.py | `search_systems` | 자연어 의미론적 시스템 검색 |
| | `filter_by_sso` | SSO 여부 필터링 |
| | `search_by_category` | 카테고리별 검색 |
| | `get_system_detail` | 시스템 상세 정보 조회 |
| | `get_onboarding_systems` | 신규 입사자 필수 시스템 |
| | `add_system` / `update_system` | 시스템 등록·수정 |
| user_tools.py | `set_current_user` | 세션 사용자 설정 |
| | `get_my_systems` | 내 접근 가능 시스템 조회 |
| | `add_user` | 사용자 등록 |
| | `grant_system_access` / `revoke_system_access` | 권한 부여·취소 |

---

# 도구 목록 — MCP 서버 & RAG

### MCP 서버 (mcp_servers/)

| 서버 | 도구 | 기능 |
|------|------|------|
| math_server.py | `add`, `multiply` | 수학 계산 |
| user_server.py | `load_users`, `save_users`, `find_user` | users.yaml CRUD |

### RAG 검색 (rag/)

| 문서 | 내용 |
|------|------|
| `company_rules.md` | 사내 규정 (연차·출장·경비) |
| `systems.md` | 업무용 시스템 접속 안내 (EP/VDI/Teams/이러닝) |
| `systems_personal.md` | 외부 사이트 안내 (GitLab/Jira/Jenkins/GitHub) |

> 청크 크기 300 / 오버랩 50 / Top-K 3

---

# 데이터 구조 — 사내 시스템 목록

| 시스템 | SSO | 계정 유형 | 접근 범위 |
|--------|-----|----------|----------|
| EP | ✅ | 개인계정 | 사내 |
| VDI | ✅ | 개인계정 | 사내·사외 |
| Microsoft Teams (기업형) | ✅ | 개인계정 | 사내·사외 |
| 이러닝 | ✅ | 개인계정 | 사내·사외 |
| GitHub Copilot (기업형) | ✅ | 개인계정 | 사내·사외 |
| GitLab / Jira (그룹사통합망) | ❌ | 개인계정 | 사내 |
| Jenkins (그룹사통합망) | ❌ | **공용계정** | 사내 |
| Nexus (그룹사통합망) | ❌ | **공용계정** | 사내 |
| GitHub | ❌ | 개인계정 | 사내·사외 |

---

# 데이터 구조 — 사용자 & 공용계정 관리

### users.yaml — 업무용 / 개인용 분리 구조

```yaml
systems:
  업무용:
    - EP
    - Microsoft Teams (기업형)
    - name: Jenkins (그룹사통합망)
      shared_account: Jenkins (그룹사통합망)   # 공용계정 참조
  개인용:
    - name: GitHub
      account: jinfromkorea              # 개인 계정명 저장
```

### shared_accounts.yaml — 공용계정 관리 (gitignore 처리)

```yaml
shared_accounts:
  Jenkins (그룹사통합망):
    accounts: [ace-developer]
  Nexus (그룹사통합망):
    accounts: [anonymous, poscodx-developer]
```

---

# 에이전트 역할 & 프롬프트 전략

### 안내 영역
- 계정 유형 (개인계정 EP SSO / 공용계정 팀 문의)
- 로그인 인증 수단 (EP ID+PW / SMS OTP / SSO 자동)
- 접근 수단 (브라우저 / 데스크톱 앱 / IDE 플러그인 / VDI)
- 외부 사이트 개인 계정 안내

### 핵심 규칙
| 트리거 | 동작 |
|--------|------|
| "나는 [ID]야" | `set_current_user` 즉시 호출 → 개인화 서비스 |
| "내 시스템 목록" | `get_my_systems` 호출 |
| 사외 접속 불가 시스템 | VDI 이용 방법 병행 안내 |
| 미등록 시스템 | "등록되지 않은 시스템"임을 명확히 안내 |

---

# 스킬 & 워크플로우

### 스킬 (skills/)
| 스킬 | 역할 |
|------|------|
| `system-access/SKILL.md` | 시스템 접속 안내 표준 양식 |
| `weekly-report/SKILL.md` | 주간 보고서 작성 양식 |

### Level 3 — StateGraph 워크플로우 (graph/workflow.py)

```
START → agent → (도구 호출?) → tools → agent → ... → END
```

확장 패턴 예시: 라우터, Orchestrator-Worker, Human-in-the-Loop

---

# 실행 방법

```bash
# 1. 의존성 설치
uv sync

# 2. 환경 변수 설정
cp .env.example .env
# OPENAI_API_KEY 입력

# 3. 실행
uv run chainlit run app.py
```

브라우저에서 `http://localhost:8000` 접속

---

<!-- _class: title -->

# 감사합니다
