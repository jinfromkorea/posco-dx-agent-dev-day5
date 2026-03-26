# skills/ — 스킬 (SKILL.md)

에이전트에게 도메인 전문 지식을 부여하는 모듈화된 지침입니다.
시스템 프롬프트와 달리, 스킬은 **필요할 때만 로드**됩니다 (Progressive Disclosure).

## 쉬운 방법 (추상화)

### 1단계: 스킬 폴더 + SKILL.md 생성

```
skills/
└── my-skill/
    └── SKILL.md
```

```markdown
---
name: my-skill
description: 이 스킬이 무엇을 하는지 한 줄로 설명. 에이전트가 이 설명을 보고 스킬 로드 여부를 결정합니다.
---

# 스킬 이름

## 사용 시기
- 어떤 요청이 들어왔을 때 이 스킬을 사용하는지

## 지침
- 에이전트가 따라야 할 규칙이나 양식
```

### 2단계: agent.py에서 활성화

```python
# agent.py에서 주석 해제
skills = ["./skills/"]

agent = create_deep_agent(
    ...
    skills=skills,
    backend=FilesystemBackend(root_dir=".", virtual_mode=True),
)
```

### Progressive Disclosure 동작 원리
1. 에이전트 시작 시: 프론트매터(name, description)만 로드 → 토큰 최소 소비
2. 사용자 요청이 들어오면: 에이전트가 관련 스킬을 **판단**
3. 필요한 스킬의 전체 내용을 **그때 로드**

→ 수십 개의 스킬을 등록해도 토큰 낭비가 없습니다.

## 직접 구현

### 방법 1: 시스템 프롬프트에 직접 임베딩

스킬 없이 `system.md`에 모든 지침을 넣을 수 있습니다.
단, 지침이 길어지면 토큰 낭비가 발생합니다.

```markdown
# prompts/system.md에 직접 추가
...

## 보고서 작성 시
- 반드시 다음 양식을 따르세요:
### [주간 업무 보고서]
- **보고 기간**: ...
...
```

### 방법 2: @tool로 스킬 로직을 도구화

스킬의 지침을 도구의 반환값으로 전달하는 패턴입니다.

```python
@tool
def load_report_template() -> str:
    """보고서 작성 시 사용할 템플릿을 로드합니다."""
    return Path("skills/weekly-report/SKILL.md").read_text()
```

### 방법 3: 동적 프롬프트 조립

사용자 입력을 분석하여 필요한 지침만 프롬프트에 추가합니다.

```python
def build_dynamic_prompt(user_message: str) -> str:
    base = "당신은 AI 어시스턴트입니다."
    if "보고서" in user_message or "리포트" in user_message:
        skill_content = Path("skills/weekly-report/SKILL.md").read_text()
        base += f"\n\n## 활성화된 스킬\n{skill_content}"
    return base
```

## SKILL.md 작성 팁

### 좋은 description (에이전트가 이걸로 판단합니다)
```yaml
# 좋음: 구체적이고 트리거 키워드가 포함
description: 주간 업무 보고서를 회사 표준 양식으로 작성합니다. 보고서, 리포트, 주간 보고 요청 시 사용하세요.

# 나쁨: 너무 추상적
description: 보고서를 작성하는 스킬
```

### 프론트매터 필수 필드
```yaml
---
name: my-skill          # 소문자 + 하이픈, 최대 64자
description: ...        # 최대 1024자, 매칭에 사용
---
```

## 스킬 아이디어

| 스킬 | 설명 | 트리거 |
|------|------|--------|
| 주간 보고서 | 표준 양식 보고서 (예시 제공됨) | "보고서", "리포트" |
| 코드 리뷰 | 보안/성능/가독성 체크리스트 | "리뷰", "코드 검토" |
| 회의록 | 회의록 양식 | "회의록", "미팅 노트" |
| 이메일 초안 | 공식 이메일 양식 | "이메일", "메일 작성" |
| 기술 문서 | API 문서 양식 | "문서화", "API 문서" |
