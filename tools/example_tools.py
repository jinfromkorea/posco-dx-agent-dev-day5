"""
커스텀 도구 예시 — @tool 데코레이터로 도구를 정의합니다.

이 파일의 도구들은 tools/__init__.py에 의해 자동 수집됩니다.
새 도구를 추가하려면 이 파일에 함수를 추가하거나,
새로운 *_tools.py 파일을 만드세요.
"""

from datetime import datetime

from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """현재 날짜와 시간을 반환합니다. 오늘 날짜나 현재 시간을 물어볼 때 사용하세요.

    Returns:
        현재 날짜와 시간 문자열
    """
    now = datetime.now()
    return now.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")


# ── 아래에 새 도구를 추가하세요 ──────────────────────────────


@tool
def calculate(expression: str) -> str:
    """수학 계산을 수행합니다. 사칙연산, 거듭제곱 등을 계산할 때 사용하세요.

    Args:
        expression: 계산할 수식 (예: "2 + 3 * 4", "2 ** 10")
    """
    result = eval(expression)
    return f"{expression} = {result}"
