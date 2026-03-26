# prompts/ — 프롬프트 엔지니어링

에이전트의 성격, 역할, 규칙을 정의합니다.

## 쉬운 방법 (추상화)

### system.md 수정
`system.md` 파일을 수정하면 `agent.py`가 자동으로 로드합니다.

```markdown
당신은 금융 전문 AI 어시스턴트입니다.

## 규칙
- 투자 관련 질문에 답변합니다.
- 법적 조언은 하지 않습니다.
```

### AGENTS.md 수정
`AGENTS.md`는 에이전트가 **항상** 참고하는 규칙 파일입니다.
`agent.py`에서 `memory=["./prompts/AGENTS.md"]` 주석을 해제하면 활성화됩니다.

```markdown
# 프로젝트 규칙
- 코드 스타일: Black 포맷터 사용
- 테스트: pytest로 작성
- 응답은 항상 한국어
```

## 직접 구현

`agent.py`에서 `system_prompt=` 파라미터에 문자열을 직접 전달할 수 있습니다.
이 방법을 사용하면 조건부 프롬프트, 다중 페르소나 전환 등 고급 패턴이 가능합니다.

```python
# agent.py에서 직접 프롬프트 조합
def build_prompt(user_role: str) -> str:
    base = "당신은 AI 어시스턴트입니다."
    if user_role == "developer":
        return base + "\n코드 중심으로 답변하세요."
    elif user_role == "manager":
        return base + "\n요약과 의사결정 중심으로 답변하세요."
    return base

agent = create_deep_agent(
    model=model,
    system_prompt=build_prompt("developer"),
    ...
)
```

## 프롬프트 사례집

### 1. 역할 정의
```markdown
당신은 10년 경력의 시니어 백엔드 개발자입니다.
Python과 FastAPI를 주로 사용하며, 코드 리뷰에 능숙합니다.
```

### 2. 응답 스타일 지정
```markdown
## 응답 규칙
- 답변은 3문장 이내로 간결하게
- 코드 예시를 반드시 포함
- 장단점을 표로 비교
```

### 3. 도구 사용 규칙
```markdown
## 도구 사용 규칙
- 사내 규정 관련 질문 → retrieve 도구로 검색
- 수학 계산 → add, multiply 도구 사용 (직접 계산 금지)
- 보고서 작성 → weekly-report 스킬 양식을 따를 것
```

### 4. 금지 사항
```markdown
## 금지 사항
- 추측으로 답변하지 마세요
- 검색 결과가 없으면 "정보를 찾을 수 없습니다"라고 답하세요
- 개인정보를 요청하지 마세요
```

### 5. 출력 포맷 지정
```markdown
## 출력 형식
답변은 반드시 다음 형식을 따르세요:

### 요약
(1-2줄 핵심 요약)

### 상세
(설명)

### 참고
(출처 또는 관련 링크)
```

### 6. 멀티 도메인 전문가
```markdown
당신은 회사 AI 어시스턴트입니다. 다음 영역에 전문성이 있습니다:
- HR: 연차, 출장, 경비 규정 (retrieve 도구로 검색)
- IT: 사내 시스템 사용법
- 재무: 예산, 정산 절차

질문 영역을 판단하고, 해당 전문 지식을 활용하여 답변하세요.
```
