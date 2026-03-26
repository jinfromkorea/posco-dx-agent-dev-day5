# tools/ — 커스텀 도구

에이전트가 호출할 수 있는 도구(함수)를 정의합니다.

## 쉬운 방법 (추상화)

`tools/` 폴더에 `*_tools.py` 파일을 만들고 `@tool` 함수를 작성하면 **자동으로 수집**됩니다.

### 1단계: 도구 함수 작성

```python
# tools/my_tools.py
from langchain_core.tools import tool

@tool
def greet(name: str) -> str:
    """사용자에게 인사합니다.

    Args:
        name: 인사할 사람의 이름
    """
    return f"안녕하세요, {name}님!"
```

### 2단계: 끝!

`__init__.py`가 자동으로 수집하므로, `agent.py`에서 별도 작업이 필요 없습니다.

```python
# agent.py (이미 되어 있음)
from tools import all_tools
tools = [*all_tools]  # 자동으로 greet 포함
```

### 주의사항

- 파일 이름이 `_tools.py`로 끝나야 자동 수집됩니다 (예: `my_tools.py`, `api_tools.py`)
- `@tool` 데코레이터의 **docstring이 중요**합니다. 에이전트가 이 설명을 보고 도구 호출 여부를 결정합니다
- `Args:` 섹션으로 파라미터 설명을 추가하면 에이전트가 더 정확하게 사용합니다

## 직접 구현

### 클래스 기반 도구 (BaseTool)

더 복잡한 도구는 `BaseTool`을 상속하여 만들 수 있습니다.

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="검색할 키워드")
    max_results: int = Field(default=5, description="최대 결과 수")

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "웹에서 정보를 검색합니다."
    args_schema: type[BaseModel] = SearchInput

    def _run(self, query: str, max_results: int = 5) -> str:
        # 실제 검색 로직
        return f"'{query}' 검색 결과 {max_results}건"

# agent.py에서 직접 추가
tools = [*all_tools, WebSearchTool()]
```

### content_and_artifact 패턴

RAG 등에서 모델용 텍스트와 원본 객체를 분리할 때 유용합니다.

```python
@tool(response_format="content_and_artifact")
def retrieve(query: str):
    """지식 베이스에서 관련 문서를 검색합니다."""
    results = vector_store.similarity_search(query, k=3)
    text = "\n".join(doc.page_content for doc in results)
    return text, results  # (모델용 텍스트, 원본 Document 리스트)
```

### StructuredTool (함수에서 변환)

기존 함수를 도구로 변환할 때 유용합니다.

```python
from langchain_core.tools import StructuredTool

def my_function(x: int, y: int) -> int:
    return x + y

tool = StructuredTool.from_function(
    func=my_function,
    name="add_numbers",
    description="두 숫자를 더합니다",
)
```

## 도구 아이디어

| 도구 | 설명 | 난이도 |
|------|------|--------|
| 현재 시간 | `datetime.now()` 반환 | 쉬움 |
| 날씨 조회 | 외부 API 호출 | 보통 |
| DB 조회 | SQLite/PostgreSQL 쿼리 | 보통 |
| 웹 스크래핑 | URL에서 텍스트 추출 | 보통 |
| 이메일 발송 | SMTP로 메일 전송 | 어려움 |
| Slack 메시지 | Slack API로 메시지 전송 | 어려움 |
