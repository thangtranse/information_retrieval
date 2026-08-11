# Crawled Article Preprocessing with VnCoreNLP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đọc các file UTF-8 được liên kết từ `crawl_urls.file_path`, giữ lại metadata của từng block `<s>`, chuẩn hóa nội dung, tách từ bằng VnCoreNLP và lưu kết quả có quan hệ với `crawl_urls` trong PostgreSQL.

**Architecture:** Application use case điều phối một batch tuần tự gồm crawl-row reader, article-file reader, text normalizer, VnCoreNLP adapter và processed-paragraph repository. Một bảng mới `processed_paragraphs` liên kết với `crawl_urls.id` bằng foreign key; mỗi row tương ứng đúng một block nguồn và lưu `segmented_sentences` dưới dạng PostgreSQL JSONB. File path luôn được resolve từ thư mục `backend/`, không phụ thuộc current working directory; việc thay thế toàn bộ paragraph của một crawl row diễn ra trong một transaction để lần chạy lại không để lại dữ liệu cũ.

**Tech Stack:** Python 3.14, uv, SQLAlchemy 2, PostgreSQL 17 + JSONB, BeautifulSoup4, py-vncorenlp 0.1.4+, VnCoreNLP 1.2, Java runtime, Ruff, mypy.

## Global Constraints

- Không tạo hoặc yêu cầu automated tests; verification dùng Ruff, mypy, build hiện có và manual smoke checks theo `AGENTS.md`.
- Chạy backend commands từ `backend/` hoặc dùng root `Makefile`; dependency Python chỉ quản lý bằng `uv`.
- Domain và application không import SQLAlchemy, BeautifulSoup, py-vncorenlp hoặc framework khác.
- Mọi function/method chứa business logic phải có docstring/comment giải thích WHY, không mô tả WHAT hiển nhiên.
- Chỉ xử lý `crawl_urls.status = 'completed'` và `file_path IS NOT NULL`, theo thứ tự `crawl_urls.id` tăng dần.
- `crawl_url_id` là quan hệ chính thức; không dùng `file_path` làm foreign key vì path có thể thay đổi và không có uniqueness constraint.
- `docid` đọc từ file phải bằng `crawl_urls.id`; `num` và thứ tự block trong file phải được giữ nguyên.
- Literal entity `&gt;` phải bị loại bỏ trước khi decode HTML entities; các ký tự `>` hợp lệ không bắt nguồn từ literal `&gt;` không bị xóa.
- VnCoreNLP được load đúng một lần cho mỗi process batch; model chỉ được download khi người dùng chạy command download và model chưa tồn tại.
- Batch chạy tuần tự. Một file lỗi được ghi vào summary và không làm mất processed data hợp lệ từ lần chạy trước của file đó.
- Không sửa hoặc đưa vào commit thư mục untracked `backend/notebook/analysisData/`.

---

## File Structure

```text
backend/
├── Dockerfile                                             # cài Java runtime cho VnCoreNLP
├── .env.example                                           # cấu hình model directory
├── data/models/py_vncorenlp/.gitkeep                      # model cache hiện có, không commit model
└── src/information_retrieval/
    ├── domain/
    │   └── preprocessing.py                               # SourceParagraph, ProcessedParagraph, summary và errors
    ├── application/
    │   ├── preprocessing_ports.py                         # reader/segmenter/repository ports
    │   └── preprocess_crawled_articles.py                 # batch use case tuần tự
    ├── infrastructure/
    │   ├── config.py                                      # segmenter_model_dir
    │   ├── database.py                                    # processed_paragraphs ORM table
    │   ├── crawl_repository.py                            # query completed crawl rows
    │   ├── article_paragraph_reader.py                    # resolve path + parse `<s>` blocks
    │   ├── vncorenlp_segmenter.py                         # model presence/download/load/word_segment
    │   └── processed_paragraph_repository.py              # transactional replacement per crawl row
    └── presentation/cli/
        └── preprocess.py                                  # download/process CLI entrypoint
Makefile                                                   # preprocess/download targets
README.md                                                  # prerequisites, commands, schema behavior
```

## Data Contract

`processed_paragraphs` có schema sau:

| Column | Type | Constraint / meaning |
|---|---|---|
| `id` | `BIGINT` | Primary key, auto increment |
| `crawl_url_id` | `BIGINT` | FK `crawl_urls.id ON DELETE CASCADE`, not null |
| `docid` | `BIGINT` | Giá trị từ attribute `docid`; check bằng `crawl_url_id` |
| `paragraph_num` | `INTEGER` | Giá trị gốc từ attribute `num`, positive |
| `block_type` | `VARCHAR(16)` | `title`, `description` hoặc `paragraph` |
| `source_word_count` | `INTEGER` | Giá trị gốc từ attribute `wdcount`, non-negative |
| `source_text` | `TEXT` | Nội dung sau bỏ thẻ `<s>` và decode entity |
| `normalized_text` | `TEXT` | Nội dung sau CHAR_MAP, xóa invisible chars và collapse space/tab |
| `segmented_sentences` | `JSONB` | `list[str]` trả về từ `word_segment` theo đúng thứ tự |
| `created_at` | timezone-aware timestamp | Thời điểm row hiện tại được tạo |
| `updated_at` | timezone-aware timestamp | Thời điểm row hiện tại được ghi |

Unique constraint `(crawl_url_id, paragraph_num)` bảo đảm một block nguồn chỉ có một kết quả hiện hành. Mỗi document được validate, normalize và segment hoàn chỉnh trước khi repository mở transaction xóa các row cũ và insert snapshot mới.

---

### Task 1: Domain contracts and preprocessing ports

**Files:**
- Create: `backend/src/information_retrieval/domain/preprocessing.py`
- Create: `backend/src/information_retrieval/application/preprocessing_ports.py`

**Interfaces:**
- Consumes: `CrawlUrl` từ `information_retrieval.domain.crawl`.
- Produces: `SourceParagraph`, `ProcessedParagraph`, `PreprocessingFailure`, `PreprocessingSummary`, `ArticlePreprocessingError`, `normalize_article_text(raw_text: str) -> str`, `CompletedCrawlRepository`, `ArticleParagraphReader`, `WordSegmenter`, `ProcessedParagraphRepository`.

- [ ] **Step 1: Define immutable domain records and typed failure**

Create `domain/preprocessing.py` with these exact public contracts:

```python
from dataclasses import dataclass
import re

from information_retrieval.domain.article import BlockType

CHAR_MAP = {
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "–": "-",
    "—": "-",
}


class ArticlePreprocessingError(Exception):
    """Expose expected per-document failures so a batch can continue without hiding bugs."""


@dataclass(frozen=True, slots=True)
class SourceParagraph:
    docid: int
    num: int
    source_word_count: int
    block_type: BlockType
    text: str


@dataclass(frozen=True, slots=True)
class ProcessedParagraph:
    docid: int
    num: int
    source_word_count: int
    block_type: BlockType
    source_text: str
    normalized_text: str
    segmented_sentences: list[str]


@dataclass(frozen=True, slots=True)
class PreprocessingFailure:
    crawl_url_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class PreprocessingSummary:
    selected_documents: int
    processed_documents: int
    stored_paragraphs: int
    failures: list[PreprocessingFailure]


def normalize_article_text(raw_text: str) -> str:
    """Keep model input stable across typographic variants and invisible crawl artifacts."""
    normalized = raw_text.replace("&gt;", "")
    for source, target in CHAR_MAP.items():
        normalized = normalized.replace(source, target)
    normalized = normalized.replace("\u200b", "")
    normalized = normalized.replace("\ufeff", "")
    normalized = normalized.replace("\xa0", " ")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()
```

The implementation must reject empty normalized text in the application use case instead of storing an unusable model input.

- [ ] **Step 2: Define narrow application-owned ports**

Create `application/preprocessing_ports.py`:

```python
from typing import Protocol

from information_retrieval.domain.crawl import CrawlUrl
from information_retrieval.domain.preprocessing import ProcessedParagraph, SourceParagraph


class CompletedCrawlRepository(Protocol):
    def list_completed(self, crawl_id: int | None = None) -> list[CrawlUrl]:
        """Limit preprocessing to durable article files and retain deterministic id order."""
        ...


class ArticleParagraphReader(Protocol):
    def read(self, crawl_id: int, file_path: str) -> list[SourceParagraph]:
        """Return validated source blocks without leaking file or parser details inward."""
        ...


class WordSegmenter(Protocol):
    def segment(self, text: str) -> list[str]:
        """Hide the Java-backed NLP runtime behind a deterministic application boundary."""
        ...


class ProcessedParagraphRepository(Protocol):
    def initialize_schema(self) -> None:
        """Create the processing table idempotently for CLI execution against a fresh DB."""
        ...

    def replace_for_crawl_url(
        self, crawl_url_id: int, paragraphs: list[ProcessedParagraph]
    ) -> None:
        """Replace one document atomically so stale blocks cannot survive a rerun."""
        ...
```

- [ ] **Step 3: Run static checks for the new inner-layer contracts**

Run:

```bash
cd backend
uv run ruff format src/information_retrieval/domain/preprocessing.py src/information_retrieval/application/preprocessing_ports.py
uv run ruff check src/information_retrieval/domain/preprocessing.py src/information_retrieval/application/preprocessing_ports.py
uv run mypy src
```

Expected: Ruff prints `All checks passed!`; mypy prints `Success: no issues found`.

- [ ] **Step 4: Commit the domain boundary**

```bash
git add backend/src/information_retrieval/domain/preprocessing.py backend/src/information_retrieval/application/preprocessing_ports.py
git commit -m "feat: define article preprocessing contracts"
```

---

### Task 2: Source file selection, path resolution, and `<s>` parsing

**Files:**
- Modify: `backend/src/information_retrieval/infrastructure/crawl_repository.py`
- Create: `backend/src/information_retrieval/infrastructure/article_paragraph_reader.py`

**Interfaces:**
- Consumes: `CompletedCrawlRepository.list_completed(crawl_id)` and `SourceParagraph` from Task 1; existing `CrawlUrlRow`, `CrawlUrl`, and backend-relative `file_path` contract.
- Produces: `PostgresCrawlUrlRepository.list_completed(crawl_id: int | None = None) -> list[CrawlUrl]`; `Utf8ArticleParagraphReader.read(crawl_id: int, file_path: str) -> list[SourceParagraph]`.

- [ ] **Step 1: Add the stable completed-row query**

Add this method to `PostgresCrawlUrlRepository`:

```python
def list_completed(self, crawl_id: int | None = None) -> list[CrawlUrl]:
    """Only expose durable files, in id order, so reruns are reproducible and auditable."""
    with Session(self._engine) as session:
        statement = select(CrawlUrlRow).where(
            CrawlUrlRow.status == "completed",
            CrawlUrlRow.file_path.is_not(None),
        )
        if crawl_id is not None:
            statement = statement.where(CrawlUrlRow.id == crawl_id)
        rows = session.scalars(statement.order_by(CrawlUrlRow.id)).all()
        return [self._to_domain(row) for row in rows]
```

- [ ] **Step 2: Implement backend-anchored path resolution**

In `article_paragraph_reader.py`, define `_BACKEND_ROOT = Path(__file__).resolve().parents[3]` and use this resolution rule:

```python
def _resolve_backend_path(stored_path: str) -> Path:
    """Anchor persisted relative paths to backend so CLI cwd cannot redirect file access."""
    raw_path = Path(stored_path)
    if raw_path.is_absolute():
        candidate = raw_path.resolve()
    elif raw_path.parts and raw_path.parts[0] == "backend":
        candidate = (_BACKEND_ROOT.parent / raw_path).resolve()
    else:
        candidate = (_BACKEND_ROOT / raw_path).resolve()

    if not candidate.is_relative_to(_BACKEND_ROOT):
        raise ArticlePreprocessingError(
            f"file_path escapes backend directory: {stored_path}"
        )
    return candidate
```

This supports both the current DB value `data/articles/261.txt` and project-root notation `backend/data/articles/261.txt`, while rejecting path traversal and absolute files outside `backend/`.

- [ ] **Step 3: Parse and validate all `<s>` blocks**

Implement `Utf8ArticleParagraphReader.read` with BeautifulSoup's built-in `html.parser` and these invariants:

```python
class Utf8ArticleParagraphReader:
    _ALLOWED_TYPES = {"title", "description", "paragraph"}

    def read(self, crawl_id: int, file_path: str) -> list[SourceParagraph]:
        """Fail the whole document before persistence when source metadata is inconsistent."""
        resolved_path = _resolve_backend_path(file_path)
        try:
            serialized = resolved_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ArticlePreprocessingError(
                f"cannot read UTF-8 article file {file_path}: {error}"
            ) from error

        # The corpus serializer represents source `>` characters as this literal entity;
        # removing it before HTML decoding satisfies the preprocessing contract without
        # deleting unrelated, already-decoded greater-than characters.
        soup = BeautifulSoup(serialized.replace("&gt;", ""), "html.parser")
        paragraphs: list[SourceParagraph] = []
        for tag in soup.find_all("s"):
            try:
                docid = int(str(tag["docid"]))
                num = int(str(tag["num"]))
                source_word_count = int(str(tag["wdcount"]))
                block_type = str(tag["type"])
            except (KeyError, TypeError, ValueError) as error:
                raise ArticlePreprocessingError(
                    f"invalid <s> metadata in {file_path}"
                ) from error

            if docid != crawl_id:
                raise ArticlePreprocessingError(
                    f"docid {docid} does not match crawl_urls.id {crawl_id}"
                )
            if num <= 0 or source_word_count < 0 or block_type not in self._ALLOWED_TYPES:
                raise ArticlePreprocessingError(
                    f"invalid <s> values for crawl_urls.id {crawl_id}, num {num}"
                )
            if paragraphs and num <= paragraphs[-1].num:
                raise ArticlePreprocessingError(
                    f"paragraph num is not strictly increasing for crawl_urls.id {crawl_id}"
                )

            text = tag.get_text(separator=" ", strip=True)
            paragraphs.append(
                SourceParagraph(
                    docid=docid,
                    num=num,
                    source_word_count=source_word_count,
                    block_type=cast(BlockType, block_type),
                    text=text,
                )
            )

        if not paragraphs:
            raise ArticlePreprocessingError(f"no valid <s> blocks in {file_path}")
        return paragraphs
```

Add exact imports for `Path`, `cast`, `BeautifulSoup`, `BlockType`, `SourceParagraph`, and `ArticlePreprocessingError`. `BeautifulSoup` removes the surrounding `<s>` tag and decodes remaining entities such as `&amp;` and `&lt;`; attributes remain available for metadata validation.

- [ ] **Step 4: Run a read-only parser smoke check against an existing file**

Run from `backend/`:

```bash
uv run python -c 'from information_retrieval.infrastructure.article_paragraph_reader import Utf8ArticleParagraphReader; rows = Utf8ArticleParagraphReader().read(1000, "data/articles/1000.txt"); print(rows[0].docid, rows[0].num, rows[0].block_type, len(rows))'
```

Expected: output begins `1000 1 title` and the final number is greater than `2`. This check reads only the file and does not write database state.

- [ ] **Step 5: Format, check, and commit the reader slice**

```bash
cd backend
uv run ruff format src/information_retrieval/infrastructure/crawl_repository.py src/information_retrieval/infrastructure/article_paragraph_reader.py
uv run ruff check src/information_retrieval/infrastructure/crawl_repository.py src/information_retrieval/infrastructure/article_paragraph_reader.py
uv run mypy src
cd ..
git add backend/src/information_retrieval/infrastructure/crawl_repository.py backend/src/information_retrieval/infrastructure/article_paragraph_reader.py
git commit -m "feat: read crawled article paragraphs"
```

---

### Task 3: Processed paragraph table and transactional persistence

**Files:**
- Modify: `backend/src/information_retrieval/infrastructure/database.py`
- Create: `backend/src/information_retrieval/infrastructure/processed_paragraph_repository.py`

**Interfaces:**
- Consumes: `ProcessedParagraphRepository.replace_for_crawl_url` and `ProcessedParagraph` from Task 1; existing `initialize_schema(engine)`.
- Produces: `ProcessedParagraphRow`; `PostgresProcessedParagraphRepository.initialize_schema()`; `PostgresProcessedParagraphRepository.replace_for_crawl_url(crawl_url_id, paragraphs)`.

- [ ] **Step 1: Add the `processed_paragraphs` ORM model**

Extend imports in `database.py` with `ForeignKey`, `Integer`, `UniqueConstraint` and `JSONB` from `sqlalchemy.dialects.postgresql`. Add:

```python
class ProcessedParagraphRow(Base):
    __tablename__ = "processed_paragraphs"
    __table_args__ = (
        UniqueConstraint(
            "crawl_url_id",
            "paragraph_num",
            name="processed_paragraphs_crawl_num_key",
        ),
        CheckConstraint(
            "docid = crawl_url_id",
            name="processed_paragraphs_docid_matches_crawl_check",
        ),
        CheckConstraint(
            "paragraph_num > 0",
            name="processed_paragraphs_num_positive_check",
        ),
        CheckConstraint(
            "source_word_count >= 0",
            name="processed_paragraphs_word_count_check",
        ),
        CheckConstraint(
            "block_type IN ('title', 'description', 'paragraph')",
            name="processed_paragraphs_type_check",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    crawl_url_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_urls.id", ondelete="CASCADE"), nullable=False
    )
    docid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paragraph_num: Mapped[int] = mapped_column(Integer, nullable=False)
    block_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    segmented_sentences: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

Keep the existing `Base.metadata.create_all(engine)` path. It creates only the missing table and does not mutate the existing `crawl_urls` contract.

- [ ] **Step 2: Implement atomic document replacement**

Create `processed_paragraph_repository.py` with `PostgresProcessedParagraphRepository(engine: Engine)`. Its write method must use one `Session` transaction:

```python
def replace_for_crawl_url(
    self, crawl_url_id: int, paragraphs: list[ProcessedParagraph]
) -> None:
    """Swap a full document snapshot atomically so failures retain the previous good result."""
    if not paragraphs:
        raise ArticlePreprocessingError(
            f"refusing to persist an empty document for crawl_urls.id {crawl_url_id}"
        )

    with Session(self._engine) as session, session.begin():
        session.execute(
            delete(ProcessedParagraphRow).where(
                ProcessedParagraphRow.crawl_url_id == crawl_url_id
            )
        )
        session.add_all(
            [
                ProcessedParagraphRow(
                    crawl_url_id=crawl_url_id,
                    docid=paragraph.docid,
                    paragraph_num=paragraph.num,
                    block_type=paragraph.block_type,
                    source_word_count=paragraph.source_word_count,
                    source_text=paragraph.source_text,
                    normalized_text=paragraph.normalized_text,
                    segmented_sentences=paragraph.segmented_sentences,
                )
                for paragraph in paragraphs
            ]
        )
```

`initialize_schema()` delegates to the existing `initialize_schema(self._engine)`. Do not catch SQLAlchemy write errors: the transaction must roll back and a database/constraint failure must stop the command instead of being mislabeled as a bad source file.

- [ ] **Step 3: Create the table and verify constraints through PostgreSQL metadata**

With the existing Postgres container running, execute:

```bash
cd backend
uv run python -c 'from information_retrieval.infrastructure.config import get_settings; from information_retrieval.infrastructure.database import create_database_engine; from information_retrieval.infrastructure.processed_paragraph_repository import PostgresProcessedParagraphRepository; PostgresProcessedParagraphRepository(create_database_engine(get_settings().database_url)).initialize_schema(); print("schema initialized")'
```

Then run from project root:

```bash
docker compose exec -T postgres psql -U information_retrieval -d information_retrieval -c '\d+ processed_paragraphs'
```

Expected: table lists the foreign key to `crawl_urls`, unique key on `(crawl_url_id, paragraph_num)`, JSONB `segmented_sentences`, and all four check constraints described above.

- [ ] **Step 4: Format, statically verify, and commit persistence**

```bash
cd backend
uv run ruff format src/information_retrieval/infrastructure/database.py src/information_retrieval/infrastructure/processed_paragraph_repository.py
uv run ruff check src/information_retrieval/infrastructure/database.py src/information_retrieval/infrastructure/processed_paragraph_repository.py
uv run mypy src
cd ..
git add backend/src/information_retrieval/infrastructure/database.py backend/src/information_retrieval/infrastructure/processed_paragraph_repository.py
git commit -m "feat: persist processed article paragraphs"
```

---

### Task 4: VnCoreNLP adapter and sequential preprocessing use case

**Files:**
- Create: `backend/src/information_retrieval/infrastructure/vncorenlp_segmenter.py`
- Create: `backend/src/information_retrieval/application/preprocess_crawled_articles.py`

**Interfaces:**
- Consumes: all Task 1 ports, `normalize_article_text`, Task 2 reader/repository, Task 3 processed repository.
- Produces: `VnCoreNlpWordSegmenter`; `VnCoreNlpWordSegmenter.is_model_installed(model_dir) -> bool`; `VnCoreNlpWordSegmenter.download_model(model_dir) -> bool`; `PreprocessCrawledArticles.execute(crawl_id: int | None = None) -> PreprocessingSummary`.

- [ ] **Step 1: Implement explicit model installation and one-time segmenter loading**

Create `vncorenlp_segmenter.py` with these rules:

```python
class VnCoreNlpWordSegmenter:
    _JAR_NAME = "VnCoreNLP-1.2.jar"

    def __init__(self, model_dir: Path) -> None:
        if not self.is_model_installed(model_dir):
            raise ArticlePreprocessingError(
                f"VnCoreNLP model is missing at {model_dir}; run make download-segmenter-model"
            )
        try:
            self._segmenter = py_vncorenlp.VnCoreNLP(
                annotators=["wseg"], save_dir=str(model_dir)
            )
        except Exception as error:
            raise ArticlePreprocessingError(
                f"cannot load VnCoreNLP model from {model_dir}: {error}"
            ) from error

    @classmethod
    def is_model_installed(cls, model_dir: Path) -> bool:
        """Avoid a network call when both the runtime jar and word segmenter already exist."""
        return (model_dir / cls._JAR_NAME).is_file() and (
            model_dir / "models" / "wordsegmenter"
        ).is_dir()

    @classmethod
    def download_model(cls, model_dir: Path) -> bool:
        """Keep model download explicit because preprocessing should be offline-repeatable."""
        if cls.is_model_installed(model_dir):
            return False
        model_dir.mkdir(parents=True, exist_ok=True)
        py_vncorenlp.download_model(save_dir=str(model_dir))
        if not cls.is_model_installed(model_dir):
            raise ArticlePreprocessingError(
                f"VnCoreNLP download did not produce a usable model at {model_dir}"
            )
        return True

    def segment(self, text: str) -> list[str]:
        """Translate library/runtime failures into a per-document batch failure."""
        try:
            return cast(list[str], self._segmenter.word_segment(text))
        except Exception as error:
            raise ArticlePreprocessingError(f"VnCoreNLP segmentation failed: {error}") from error
```

Import `py_vncorenlp` with the narrow `# type: ignore[import-untyped]` only if mypy confirms the installed package has no type marker. Do not globally disable missing-import checking.

- [ ] **Step 2: Implement batch orchestration without partial document writes**

Create `preprocess_crawled_articles.py`. Constructor dependencies are the four Task 1 ports. Implement:

```python
class PreprocessCrawledArticles:
    def __init__(
        self,
        crawl_repository: CompletedCrawlRepository,
        reader: ArticleParagraphReader,
        segmenter: WordSegmenter,
        processed_repository: ProcessedParagraphRepository,
    ) -> None:
        self._crawl_repository = crawl_repository
        self._reader = reader
        self._segmenter = segmenter
        self._processed_repository = processed_repository

    def execute(self, crawl_id: int | None = None) -> PreprocessingSummary:
        """Isolate expected document failures while preserving prior successful snapshots."""
        crawl_rows = self._crawl_repository.list_completed(crawl_id)
        processed_documents = 0
        stored_paragraphs = 0
        failures: list[PreprocessingFailure] = []

        for crawl_row in crawl_rows:
            assert crawl_row.file_path is not None
            try:
                source_paragraphs = self._reader.read(crawl_row.id, crawl_row.file_path)
                processed: list[ProcessedParagraph] = []
                for source in source_paragraphs:
                    normalized_text = normalize_article_text(source.text)
                    if not normalized_text:
                        raise ArticlePreprocessingError(
                            f"empty normalized text at paragraph num {source.num}"
                        )
                    segmented_sentences = self._segmenter.segment(normalized_text)
                    if not segmented_sentences:
                        raise ArticlePreprocessingError(
                            f"no segmented sentences at paragraph num {source.num}"
                        )
                    processed.append(
                        ProcessedParagraph(
                            docid=source.docid,
                            num=source.num,
                            source_word_count=source.source_word_count,
                            block_type=source.block_type,
                            source_text=source.text,
                            normalized_text=normalized_text,
                            segmented_sentences=segmented_sentences,
                        )
                    )
                self._processed_repository.replace_for_crawl_url(crawl_row.id, processed)
            except ArticlePreprocessingError as error:
                failures.append(
                    PreprocessingFailure(crawl_url_id=crawl_row.id, reason=str(error))
                )
                continue

            processed_documents += 1
            stored_paragraphs += len(processed)

        return PreprocessingSummary(
            selected_documents=len(crawl_rows),
            processed_documents=processed_documents,
            stored_paragraphs=stored_paragraphs,
            failures=failures,
        )
```

Do not catch arbitrary `Exception` in the use case. Only expected source/model contract failures join the per-document summary; SQLAlchemy failures abort the command after transaction rollback so infrastructure faults cannot be mistaken for corrupt source text.

- [ ] **Step 3: Prove normalization with an inline, non-test smoke command**

Run:

```bash
cd backend
uv run python -c 'from information_retrieval.domain.preprocessing import normalize_article_text; value = normalize_article_text("&gt;&gt; “Xin\u200b chào”\xa0–  bạn"); print(repr(value)); assert value == "\"Xin chào\" - bạn"'
```

Expected: prints `'"Xin chào" - bạn'` and exits `0`.

- [ ] **Step 4: Verify VnCoreNLP against the existing cache without downloading**

Run:

```bash
cd backend
uv run python -c 'from pathlib import Path; from information_retrieval.infrastructure.vncorenlp_segmenter import VnCoreNlpWordSegmenter; segmenter = VnCoreNlpWordSegmenter(Path("data/models/py_vncorenlp").resolve()); print(segmenter.segment("Nghiên cứu sinh đang xử lý văn bản tiếng Việt."))'
```

Expected: exits `0` and prints a non-empty Python list. If Java is missing locally, install the documented Java prerequisite before repeating; do not download the model because the current cache already contains the jar and word-segmentation model.

- [ ] **Step 5: Format, statically verify, and commit processing logic**

```bash
cd backend
uv run ruff format src/information_retrieval/infrastructure/vncorenlp_segmenter.py src/information_retrieval/application/preprocess_crawled_articles.py
uv run ruff check src/information_retrieval/infrastructure/vncorenlp_segmenter.py src/information_retrieval/application/preprocess_crawled_articles.py
uv run mypy src
cd ..
git add backend/src/information_retrieval/infrastructure/vncorenlp_segmenter.py backend/src/information_retrieval/application/preprocess_crawled_articles.py
git commit -m "feat: preprocess articles with VnCoreNLP"
```

---

### Task 5: Configuration, CLI, local/Docker runtime, and operator documentation

**Files:**
- Modify: `backend/src/information_retrieval/infrastructure/config.py`
- Create: `backend/src/information_retrieval/presentation/cli/preprocess.py`
- Modify: `backend/.env.example`
- Modify: `backend/Dockerfile`
- Modify: `Makefile`
- Modify: `README.md`

**Interfaces:**
- Consumes: `PreprocessCrawledArticles`, all concrete adapters, `Settings.database_url`.
- Produces: `Settings.segmenter_model_dir: Path`; CLI `run(argv: list[str] | None = None) -> int`; `make download-segmenter-model`; `make preprocess`; optional focused `make preprocess ARGS=--crawl-id=261`.

- [ ] **Step 1: Add a backend-relative model setting**

In `Settings`, add:

```python
segmenter_model_dir: Path = Path("data/models/py_vncorenlp")
```

Import `Path` from `pathlib`. Add this exact line to `backend/.env.example`:

```dotenv
APP_SEGMENTER_MODEL_DIR=data/models/py_vncorenlp
```

The CLI resolves a relative configured path against `Path(__file__).resolve().parents[4]`, which is the `backend/` directory from `presentation/cli/preprocess.py`; an absolute configured path remains absolute.

- [ ] **Step 2: Implement one CLI for explicit download and batch processing**

`preprocess.py` must accept:

```python
parser.add_argument(
    "--download-model-only",
    action="store_true",
    help="download VnCoreNLP only when the configured cache is incomplete",
)
parser.add_argument(
    "--crawl-id",
    type=int,
    help="process one completed crawl_urls row instead of the full completed corpus",
)
```

`run()` builds one engine and repositories, initializes schema, and resolves the configured model path. For `--download-model-only`, call `VnCoreNlpWordSegmenter.download_model`, print either `MODEL downloaded path=...` or `MODEL cached path=...`, then return `0` without querying article rows.

For processing, construct one `VnCoreNlpWordSegmenter`, one `PreprocessCrawledArticles`, execute it, print each failure to stderr as:

```text
PREPROCESS id=<crawl-id> status=failed reason="<reason>"
```

Then print one stdout summary:

```text
SUMMARY selected=<n> processed=<n> paragraphs=<n> failed=<n>
```

Return `1` when failures are non-empty. When `--crawl-id` selects no completed row, print `PREPROCESS id=<id> status=not-found` to stderr and return `1`; an empty full corpus is a valid summary with exit code `0`.

- [ ] **Step 3: Add Make targets**

Extend `.PHONY` and add:

```make
download-segmenter-model:
	cd backend && uv run python -m information_retrieval.presentation.cli.preprocess --download-model-only

preprocess:
	cd backend && uv run python -m information_retrieval.presentation.cli.preprocess $(ARGS)
```

- [ ] **Step 4: Install Java in the backend image without changing its default command**

Before dependency sync in `backend/Dockerfile`, add:

```dockerfile
# VnCoreNLP launches its Java jar at processing time; the headless runtime avoids GUI packages.
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*
```

Keep `/app/data` as the model location under the existing Compose bind mount. Do not bake downloaded model binaries into Git or the Docker image.

- [ ] **Step 5: Document local prerequisites and operator workflow**

Update README with:

```bash
brew install wget openjdk
make download-segmenter-model
make preprocess
make preprocess ARGS=--crawl-id=261
```

Explain that:

- download prints `MODEL cached` and performs no network call when the jar and `models/wordsegmenter` already exist;
- preprocessing reads only completed `crawl_urls` rows with a non-null file path;
- DB paths `data/...` and `backend/data/...` resolve inside `backend/`;
- `processed_paragraphs` relates by `crawl_url_id`, preserves source `docid`/`num`, and stores `segmented_sentences` as JSONB;
- rerunning a document atomically replaces that document's rows;
- model downloads require network, but normal preprocessing does not.

- [ ] **Step 6: Run a focused end-to-end smoke check**

Choose an actual completed id and its path read-only:

```bash
docker compose exec -T postgres psql -U information_retrieval -d information_retrieval -Atc "SELECT id, file_path FROM crawl_urls WHERE status='completed' AND file_path IS NOT NULL ORDER BY id LIMIT 1;"
```

Use the returned numeric id in the command below in place of `1000` only when the query reports a different id:

```bash
make preprocess ARGS=--crawl-id=1000
```

Expected: one `SUMMARY selected=1 processed=1 ... failed=0` line and exit `0`. Verify persisted ordering and content:

```bash
docker compose exec -T postgres psql -U information_retrieval -d information_retrieval -c "SELECT crawl_url_id, docid, paragraph_num, block_type, normalized_text, segmented_sentences FROM processed_paragraphs WHERE crawl_url_id=1000 ORDER BY paragraph_num LIMIT 3;"
```

Expected: `crawl_url_id = docid = 1000`, paragraph numbers follow source order beginning at `1`, normalized text contains no literal `&gt;`, and every `segmented_sentences` value is a non-empty JSON array.

Run the same preprocess command a second time, then verify no duplicates:

```bash
docker compose exec -T postgres psql -U information_retrieval -d information_retrieval -Atc "SELECT COUNT(*) = COUNT(DISTINCT paragraph_num) FROM processed_paragraphs WHERE crawl_url_id=1000;"
```

Expected: `t`.

- [ ] **Step 7: Run repository verification and Docker configuration checks**

```bash
make format
make verify
docker compose config --quiet
docker compose --progress plain build backend
git status --short
```

Expected: format/lint/mypy/UI build succeed, Compose config is valid, backend image builds with Java, and `git status --short` shows only intentional task files plus the pre-existing untracked `backend/notebook/analysisData/`.

- [ ] **Step 8: Commit the runtime entrypoint and documentation**

```bash
git add backend/src/information_retrieval/infrastructure/config.py backend/src/information_retrieval/presentation/cli/preprocess.py backend/.env.example backend/Dockerfile Makefile README.md
git commit -m "feat: add article preprocessing command"
```

---

## Final Verification Checklist

- [ ] Requirement 1: completed `crawl_urls.file_path` rows are selected in stable order and paths resolve beneath `backend/`.
- [ ] Requirement 2: `<s>` tags are removed while `docid`, original `num`, `wdcount`, type, and block order are persisted.
- [ ] Requirement 3: CHAR_MAP, zero-width/BOM/NBSP cleanup, space/tab collapse, and literal `&gt;` removal match the requested preprocessing contract.
- [ ] Requirement 4: VnCoreNLP uses `annotators=["wseg"]`, loads once per batch, downloads only through the explicit command, and returns ordered `list[str]` values.
- [ ] Requirement 5: `processed_paragraphs.crawl_url_id` is a real foreign key to `crawl_urls.id`, and JSONB stores every block's segmented sentences.
- [ ] Rerun behavior: a document replacement is atomic and unique by `(crawl_url_id, paragraph_num)`.
- [ ] Failure behavior: a bad file does not delete its earlier successful snapshot and does not stop later documents.
- [ ] Repository rules: no automated tests, no UI feature changes, WHY comments present, `make verify` passes, and untracked notebook work remains untouched.
