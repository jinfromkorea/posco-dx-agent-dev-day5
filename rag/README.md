# rag/ — RAG (Retrieval-Augmented Generation)

문서를 벡터 스토어에 인덱싱하고, 에이전트가 질문에 답할 때 관련 문서를 검색합니다.

## 쉬운 방법 (추상화)

### 1단계: 문서 추가

`rag/documents/` 폴더에 `.md` 또는 `.pdf` 파일을 넣으면 자동으로 인덱싱됩니다.

```
rag/
└── documents/
    ├── company_rules.md    # 사내 규정 (예시)
    ├── product_faq.md      # 제품 FAQ
    ├── onboarding.md       # 온보딩 가이드
    └── manual.pdf          # PDF 문서도 지원
```

### 2단계: agent.py에서 활성화

```python
# agent.py에서 주석 해제
from rag.retriever import get_rag_tools

tools += get_rag_tools()
```

### 3단계: 끝!

에이전트가 관련 질문을 받으면 자동으로 `retrieve` 도구를 호출하여 문서를 검색합니다.

### 커스터마이징

`retriever.py` 상단의 설정값을 수정할 수 있습니다:

```python
CHUNK_SIZE = 300        # 청크 크기 (기본 300자)
CHUNK_OVERLAP = 50      # 청크 간 겹침 (기본 50자)
EMBEDDING_MODEL = "text-embedding-3-small"  # 임베딩 모델
TOP_K = 3               # 검색 결과 수
```

## 직접 구현

### 다양한 문서 로더

`.md`와 `.pdf`는 기본 지원됩니다. 그 외 형식을 추가하려면 `retriever.py`의 `_LOADERS` 딕셔너리에 로더를 등록하세요:

```python
# retriever.py — 새 형식 추가 예시
def _load_csv(path: Path) -> Document:
    content = path.read_text(encoding="utf-8")
    return Document(page_content=content, metadata={"source": path.name})

_LOADERS[".csv"] = _load_csv
```

또는 LangChain 커뮤니티 로더를 활용할 수도 있습니다:

```python
# 웹페이지
from langchain_community.document_loaders import WebBaseLoader
docs = WebBaseLoader("https://example.com/docs").load()

# CSV
from langchain_community.document_loaders import CSVLoader
docs = CSVLoader("rag/documents/data.csv").load()
```

### 영속 벡터 스토어

기본 `InMemoryVectorStore`는 앱 재시작 시 사라집니다. 영속 저장이 필요하면:

```python
# Chroma (로컬 영속)
from langchain_chroma import Chroma

vector_store = Chroma.from_documents(
    splits,
    embeddings,
    persist_directory="./rag/chroma_db",
)

# FAISS (로컬 영속)
from langchain_community.vectorstores import FAISS

vector_store = FAISS.from_documents(splits, embeddings)
vector_store.save_local("./rag/faiss_index")
# 로드: vector_store = FAISS.load_local("./rag/faiss_index", embeddings)
```

### 청킹 전략 커스터마이징

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 큰 청크: 더 많은 컨텍스트, 하지만 검색 정밀도 저하
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

# 작은 청크: 검색 정밀도 높지만 컨텍스트 부족 가능
splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=30)

# 마크다운 헤더 기반 분할
from langchain_text_splitters import MarkdownHeaderTextSplitter
splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
)
```

### Agentic RAG (검색 품질 향상)

검색 결과의 관련성을 평가하고, 필요하면 쿼리를 다시 작성합니다.
이 패턴은 `graph/workflow.py`의 StateGraph와 결합하면 더 강력합니다.

```python
@tool
def smart_retrieve(query: str) -> str:
    """관련성을 평가하며 검색합니다."""
    results = vector_store.similarity_search(query, k=5)

    # 관련성 필터링 (점수 기반)
    relevant = [
        doc for doc, score
        in vector_store.similarity_search_with_score(query, k=5)
        if score > 0.7
    ]

    if not relevant:
        return "관련 문서를 찾지 못했습니다. 다른 키워드로 다시 시도해주세요."

    return "\n\n".join(doc.page_content for doc in relevant)
```

## 문서 작성 팁

- 문서에 **명확한 제목**을 사용하면 검색 품질이 올라갑니다
- **메타데이터**(출처, 날짜)를 포함하면 답변에 참고 정보를 제공할 수 있습니다
- 문서가 너무 길면 청크 크기를 조절하세요
