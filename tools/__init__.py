"""
도구 자동 수집 — tools/ 폴더의 *_tools.py 파일에서 @tool 함수를 자동 수집합니다.

새 도구를 추가하려면:
1. tools/ 폴더에 my_tools.py 파일 생성
2. @tool 데코레이터로 함수 정의
3. 자동으로 all_tools에 포함됨
"""

import importlib
import pkgutil

from langchain_core.tools import BaseTool

all_tools: list[BaseTool] = []

# tools/ 폴더의 모든 *_tools.py 모듈에서 @tool 함수를 자동 수집
for _importer, module_name, _is_pkg in pkgutil.iter_modules(__path__):
    if module_name.endswith("_tools"):
        module = importlib.import_module(f".{module_name}", package=__name__)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, BaseTool):
                all_tools.append(attr)
