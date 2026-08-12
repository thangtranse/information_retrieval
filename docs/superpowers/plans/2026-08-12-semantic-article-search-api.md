# Semantic Article Search API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `POST /api/v1/search/articles`, which reuses the existing normalization,
VnCoreNLP, and PhoBERT behavior to return exact cosine-ranked, distinct related articles.

**Architecture:** Extract persistence-neutral segmentation and validated sentence encoding from the
existing batch use cases, then compose them in a new search application service. A PostgreSQL
adapter performs exact per-query-sentence cosine retrieval, and a narrowly scoped FastAPI route
maps the result to the approved HTTP contract while keeping model construction lazy.

**Tech Stack:** Python 3.14, uv, FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL 17, pgvector,
VnCoreNLP, transformers, PyTorch, Ruff, mypy, React/Vite verification tooling.

## Global Constraints

- Work only in `/Users/thangtran/Workplace/master_s_degree/information_retrieval/.worktrees/semantic-article-search-api` on branch `codex/semantic-article-search-api`; do not modify `main` or `codex/embedding-cosine-index`.
- Use Python `>=3.14,<3.15` and `uv`; do not add dependencies.
- Run `uv`/Python/Ruff/mypy commands from `backend/`, npm commands from `ui/`, and
  Git/Make/Docker commands from the worktree root unless a step states otherwise.
- Keep backend dependencies pointing inward. Domain/application code must not import FastAPI,
  SQLAlchemy, transformers, torch, or py-vncorenlp.
- Apply SOLID and keep each file focused on one current responsibility.
- Every function or method containing business logic needs a docstring/comment that explains WHY,
  never a narration of visible code.
- Do not add automated tests or a test framework. Use the explicit red probes, manual smoke scripts,
  static checks, and live API/database checks in this plan.
- Reuse `split_article_text()`, `WordSegmenter`, `SentenceEncoder`, `VnCoreNlpWordSegmenter`, and
  `PhoBertSentenceEncoder`; do not create alternate text normalization, word segmentation,
  tokenization, or pooling implementations.
- Preserve `make preprocess`, `make segment`, `make embed`, health, crawler, batch summaries,
  failure isolation, metadata propagation, and transactional persistence behavior.
- `top_k` counts distinct articles. The v1 article score is the maximum exact cosine similarity over
  all input-sentence/article-sentence pairs. Do not add ANN/HNSW search, a similarity threshold, or
  document-level embeddings.
- Query text, token IDs, masks, query vectors, and search results remain transient; the search path
  performs no writes.
- Do not change database tables, constraints, indexes, or existing data.
- Do not reformat or commit
  `backend/notebook/analysisData/analyze_txt_corpus.ipynb`; it is a known unrelated baseline Ruff
  formatting failure.
- Design source of truth:
  `docs/superpowers/specs/2026-08-12-semantic-article-search-api-design.md`.

---

## File Map

### New files

- `backend/src/information_retrieval/application/segment_normalized_text_parts.py`: shared,
  persistence-neutral VnCoreNLP orchestration and 200-word guard.
- `backend/src/information_retrieval/application/encode_sentence_texts.py`: shared PhoBERT batching
  and vector-output validation.
- `backend/src/information_retrieval/domain/search.py`: search errors and immutable candidate/result
  types.
- `backend/src/information_retrieval/application/search_ports.py`: exact article-search repository
  port.
- `backend/src/information_retrieval/application/search_articles.py`: raw-text-to-ranked-articles
  orchestration, model lock, max-pair merge, and stable ordering.
- `backend/src/information_retrieval/infrastructure/article_search_repository.py`: exact PostgreSQL
  `DISTINCT ON` cosine query.
- `backend/src/information_retrieval/infrastructure/model_paths.py`: one backend-relative model-cache
  resolver shared by the two CLIs and HTTP composition.
- `backend/src/information_retrieval/presentation/http/routes/search.py`: request execution, error
  mapping, response projection, timing, and terminal logging.

### Modified files

- `backend/src/information_retrieval/domain/segmentation.py`: add request-independent normalized-part
  and text-segment domain values.
- `backend/src/information_retrieval/application/segment_processed_paragraphs.py`: delegate existing
  segmentation business rules to the shared service, then restore persistent metadata.
- `backend/src/information_retrieval/domain/embedding.py`: add ordered sentence-input and validated
  encoded-output values.
- `backend/src/information_retrieval/application/embed_segmented_sentences.py`: delegate batching and
  vector validation to the shared encoder service.
- `backend/src/information_retrieval/presentation/cli/segment.py`: reuse `resolve_model_dir()` without
  changing flags, output, or exit codes.
- `backend/src/information_retrieval/presentation/cli/embed.py`: reuse `resolve_model_dir()` without
  changing flags, output, or exit codes.
- `backend/src/information_retrieval/presentation/http/dependencies.py`: build and cache the search
  use case only on the first search request, with heavy imports inside the builder.
- `backend/src/information_retrieval/presentation/http/schemas.py`: add the approved immutable search
  request/response schemas.
- `backend/src/information_retrieval/main.py`: mount only the new search router; do not change the
  lifespan.
- `backend/.env.example`: expose already-supported PhoBERT and embedding settings.
- `README.md`: document corpus prerequisite, curl contract, lazy model load, and exact v1 ranking.

No UI file, schema model, migration, notebook, dependency file, or automated test file is created or
modified.

---

### Task 1: Extract persistence-neutral segmentation

**Files:**

- Create: `backend/src/information_retrieval/application/segment_normalized_text_parts.py`
- Modify: `backend/src/information_retrieval/domain/segmentation.py:10-34`
- Modify: `backend/src/information_retrieval/application/segment_processed_paragraphs.py:1-104`
- Manual verification only; create no test file.

**Interfaces:**

- Consumes: existing `WordSegmenter.segment(text: str) -> list[str]` and
  `MAX_PARAGRAPH_WORDS = 200`.
- Produces:
  `NormalizedTextPart(paragraph_num: int, paragraph_part_num: int, normalized_text: str)`,
  `TextSegment(paragraph_num: int, paragraph_part_num: int, segment_num: int,
segmented_text: str, segment_word_count: int)`, and
  `SegmentNormalizedTextParts.execute(parts: list[NormalizedTextPart]) -> list[TextSegment]`.
- Preserves: the public `SegmentProcessedParagraphs` constructor and
  `execute(crawl_id: int | None = None) -> SegmentationSummary` signatures.

- [ ] **Step 1: Record the missing shared-service baseline**

Run from `backend/`:

```bash
uv run python -c "from information_retrieval.application.segment_normalized_text_parts import SegmentNormalizedTextParts"
```

Expected: `ModuleNotFoundError`; this proves the red probe targets the missing extraction, not an
existing class.

- [ ] **Step 2: Add request-independent segmentation domain values**

Append these immutable values after `ArticleSegmentationError` in
`domain/segmentation.py`:

```python
@dataclass(frozen=True, slots=True)
class NormalizedTextPart:
    paragraph_num: int
    paragraph_part_num: int
    normalized_text: str


@dataclass(frozen=True, slots=True)
class TextSegment:
    paragraph_num: int
    paragraph_part_num: int
    segment_num: int
    segmented_text: str
    segment_word_count: int
```

These values deliberately omit crawl, database, and block metadata so the API cannot invent fake
persistent identifiers.

- [ ] **Step 3: Create the shared segmentation service**

Create `application/segment_normalized_text_parts.py` with this interface and behavior:

```python
from information_retrieval.application.segmentation_ports import WordSegmenter
from information_retrieval.domain.preprocessing import MAX_PARAGRAPH_WORDS
from information_retrieval.domain.segmentation import (
    ArticleSegmentationError,
    NormalizedTextPart,
    TextSegment,
)


class SegmentNormalizedTextParts:
    def __init__(self, segmenter: WordSegmenter) -> None:
        self._segmenter = segmenter

    def execute(self, parts: list[NormalizedTextPart]) -> list[TextSegment]:
        """Validate every part before model calls so a failure cannot produce partial output."""
        for part in parts:
            normalized_word_count = len(part.normalized_text.split())
            if normalized_word_count > MAX_PARAGRAPH_WORDS:
                raise ArticleSegmentationError(
                    f"paragraph num {part.paragraph_num} "
                    f"part {part.paragraph_part_num} has {normalized_word_count} "
                    f"normalized words; maximum is {MAX_PARAGRAPH_WORDS}"
                )

        segments: list[TextSegment] = []
        for part in parts:
            segmented_texts = self._segmenter.segment(part.normalized_text)
            if not segmented_texts:
                raise ArticleSegmentationError(
                    f"no segmented sentences at paragraph num {part.paragraph_num} "
                    f"part {part.paragraph_part_num}"
                )
            for segment_num, segmented_text in enumerate(segmented_texts, start=1):
                if not segmented_text.strip():
                    raise ArticleSegmentationError(
                        f"empty segmented sentence at paragraph num {part.paragraph_num} "
                        f"part {part.paragraph_part_num}"
                    )
                segments.append(
                    TextSegment(
                        paragraph_num=part.paragraph_num,
                        paragraph_part_num=part.paragraph_part_num,
                        segment_num=segment_num,
                        segmented_text=segmented_text,
                        segment_word_count=len(segmented_text.split()),
                    )
                )
        return segments
```

- [ ] **Step 4: Delegate the existing batch use case without changing its public contract**

Keep `SegmentProcessedParagraphs.__init__()` parameters unchanged. Replace its direct segmenter
field with the shared service:

```python
self._segment_parts = SegmentNormalizedTextParts(segmenter)
```

Replace `_segment_document()` with a metadata adapter whose core mapping is:

```python
text_segments = self._segment_parts.execute(
    [
        NormalizedTextPart(
            paragraph_num=paragraph.paragraph_num,
            paragraph_part_num=paragraph.paragraph_part_num,
            normalized_text=paragraph.normalized_text,
        )
        for paragraph in paragraphs
    ]
)
paragraph_by_key = {
    (paragraph.paragraph_num, paragraph.paragraph_part_num): paragraph
    for paragraph in paragraphs
}
sentences: list[SegmentedSentence] = []
for segment in text_segments:
    paragraph = paragraph_by_key[
        (segment.paragraph_num, segment.paragraph_part_num)
    ]
    sentences.append(
        SegmentedSentence(
            processed_paragraph_id=paragraph.id,
            crawl_url_id=paragraph.crawl_url_id,
            docid=paragraph.docid,
            paragraph_num=segment.paragraph_num,
            paragraph_part_num=segment.paragraph_part_num,
            block_type=paragraph.block_type,
            source_word_count=paragraph.source_word_count,
            segment_num=segment.segment_num,
            segmented_text=segment.segmented_text,
            segment_word_count=segment.segment_word_count,
        )
    )
return sentences
```

Keep `_segment_document()`'s WHY docstring: it restores durable metadata only after the shared
service has produced a complete valid document.

- [ ] **Step 5: Run a manual segmentation smoke probe**

Run this ephemeral script from `backend/`; it creates no repository file:

```bash
uv run python - <<'PY'
from information_retrieval.application.segment_normalized_text_parts import (
    SegmentNormalizedTextParts,
)
from information_retrieval.domain.preprocessing import MAX_PARAGRAPH_WORDS
from information_retrieval.domain.segmentation import (
    ArticleSegmentationError,
    NormalizedTextPart,
)


class RecordingSegmenter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def segment(self, text: str) -> list[str]:
        self.calls.append(text)
        return [f"{text}_one", f"{text}_two"]


adapter = RecordingSegmenter()
service = SegmentNormalizedTextParts(adapter)
result = service.execute(
    [
        NormalizedTextPart(1, 1, "alpha"),
        NormalizedTextPart(1, 2, "beta"),
    ]
)
assert [item.segment_num for item in result] == [1, 2, 1, 2]
assert [item.paragraph_part_num for item in result] == [1, 1, 2, 2]
assert adapter.calls == ["alpha", "beta"]

guard_adapter = RecordingSegmenter()
try:
    SegmentNormalizedTextParts(guard_adapter).execute(
        [NormalizedTextPart(3, 4, " ".join(["word"] * (MAX_PARAGRAPH_WORDS + 1)))]
    )
except ArticleSegmentationError:
    pass
else:
    raise AssertionError("the 200-word preflight guard did not reject the input")
assert guard_adapter.calls == []
print("SEGMENT_SHARED_SMOKE status=success")
PY
```

Expected: `SEGMENT_SHARED_SMOKE status=success`.

Run a second ephemeral probe for the existing persistence adapter. Use two ordered documents: one
valid document with two `StoredProcessedParagraph` rows containing distinct IDs, block types, word
counts, and paragraph-part numbers, followed by one document containing 201 normalized words. Fake
the paragraph and sentence repositories, invoke `SegmentProcessedParagraphs.execute(None)`, and
assert all of the following:

- the paragraph repository received `crawl_id=None`;
- only the valid document reached `replace_for_crawl_url()`;
- all persistent IDs, `docid`, block types, source counts, paragraph/part numbers, and per-part
  `segment_num` values were copied exactly into its `SegmentedSentence` values;
- the summary is exactly two selected documents, one segmented document, two processed paragraphs,
  four stored segments, and one failure for the oversized document;
- the invalid document caused no replacement call, proving the old snapshot remains untouched.

Print `SEGMENT_BATCH_COMPAT_SMOKE status=success` only after every assertion passes. This probe must
import and call the unchanged public constructor and `execute()` method; it must not call a private
method directly.

- [ ] **Step 6: Run mandatory formatting and focused static checks**

From the worktree root, prove the unrelated notebook was clean, run the repository-mandated
formatter, then discard only the formatter-created notebook change:

```bash
git status --short -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
make format
git restore --source=HEAD -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
git status --short -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
```

The two status commands must produce no output. Then run from `backend/`:

```bash
uv run ruff format --check src
uv run ruff check src
uv run mypy src
```

Expected: all three commands exit `0`.

- [ ] **Step 7: Commit the shared segmentation refactor**

```bash
git add backend/src/information_retrieval/domain/segmentation.py backend/src/information_retrieval/application/segment_normalized_text_parts.py backend/src/information_retrieval/application/segment_processed_paragraphs.py
git commit -m "refactor: share normalized text segmentation"
```

---

### Task 2: Extract validated sentence encoding

**Files:**

- Create: `backend/src/information_retrieval/application/encode_sentence_texts.py`
- Modify: `backend/src/information_retrieval/domain/embedding.py:1-35`
- Modify: `backend/src/information_retrieval/application/embed_segmented_sentences.py:1-96`
- Manual verification only; create no test file.

**Interfaces:**

- Consumes: existing `SentenceEncoder.encode(sentences: list[str]) -> list[list[float]]`,
  `EMBEDDING_DIMENSIONS = 768`, and configured positive batch size.
- Produces: `SentenceText(sentence_id: int, text: str)`,
  `EncodedSentence(sentence_id: int, embedding: list[float])`, and
  `EncodeSentenceTexts.execute(sentences: list[SentenceText]) -> list[EncodedSentence]`.
- Preserves: the public `EmbedSegmentedSentences` constructor and
  `execute(crawl_id: int | None = None) -> EmbeddingSummary` signatures and all repository writes.

- [ ] **Step 1: Record the missing encoder-service baseline**

From `backend/`:

```bash
uv run python -c "from information_retrieval.application.encode_sentence_texts import EncodeSentenceTexts"
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 2: Add ordered sentence input/output domain values**

Add to `domain/embedding.py`:

```python
@dataclass(frozen=True, slots=True)
class SentenceText:
    sentence_id: int
    text: str


@dataclass(frozen=True, slots=True)
class EncodedSentence:
    sentence_id: int
    embedding: list[float]
```

The integer identifier is a persistent sentence ID for `make embed` and a zero-based request-local
index for search; neither caller needs a second encoding implementation.

- [ ] **Step 3: Create the validated batching service**

Create `application/encode_sentence_texts.py`:

```python
import math

from information_retrieval.application.embedding_ports import SentenceEncoder
from information_retrieval.domain.embedding import (
    EMBEDDING_DIMENSIONS,
    EncodedSentence,
    SentenceEmbeddingError,
    SentenceText,
)


class EncodeSentenceTexts:
    def __init__(self, encoder: SentenceEncoder, batch_size: int) -> None:
        self._encoder = encoder
        self._batch_size = batch_size

    def execute(self, sentences: list[SentenceText]) -> list[EncodedSentence]:
        """Validate complete ordered batches so callers never consume partial model output."""
        if self._batch_size <= 0:
            raise SentenceEmbeddingError("embedding batch size must be greater than zero")

        encoded_sentences: list[EncodedSentence] = []
        for start in range(0, len(sentences), self._batch_size):
            batch = sentences[start : start + self._batch_size]
            vectors = self._encoder.encode([sentence.text for sentence in batch])
            if len(vectors) != len(batch):
                raise SentenceEmbeddingError(
                    f"model returned {len(vectors)} vectors for {len(batch)} sentences"
                )
            for sentence, vector in zip(batch, vectors, strict=True):
                if len(vector) != EMBEDDING_DIMENSIONS:
                    raise SentenceEmbeddingError(
                        f"sentence {sentence.sentence_id} has {len(vector)} dimensions; "
                        f"expected {EMBEDDING_DIMENSIONS}"
                    )
                if not all(math.isfinite(value) for value in vector):
                    raise SentenceEmbeddingError(
                        f"sentence {sentence.sentence_id} embedding contains a non-finite value"
                    )
                encoded_sentences.append(
                    EncodedSentence(sentence.sentence_id, vector)
                )

        if not encoded_sentences:
            raise SentenceEmbeddingError("refusing to encode an empty sentence list")
        return encoded_sentences
```

- [ ] **Step 4: Make batch embedding delegate to the shared service**

In `EmbedSegmentedSentences.__init__()`, preserve all parameters and replace the concrete encoder and
batch-size fields with:

```python
self._sentence_encoder = EncodeSentenceTexts(encoder, batch_size)
```

Replace `_encode_document()`'s batch loop with:

```python
if not sentences:
    raise SentenceEmbeddingError("refusing to persist an empty document embedding")
encoded = self._sentence_encoder.execute(
    [SentenceText(sentence.id, sentence.segmented_text) for sentence in sentences]
)
return [
    SentenceEmbedding(item.sentence_id, item.embedding)
    for item in encoded
]
```

Keep the old empty-document error in the batch use case so its failure text remains stable. Remove
the now-unused `math` import and direct `SentenceEncoder` field.

- [ ] **Step 5: Run a manual encoder smoke probe**

```bash
uv run python - <<'PY'
from information_retrieval.application.encode_sentence_texts import EncodeSentenceTexts
from information_retrieval.domain.embedding import (
    EMBEDDING_DIMENSIONS,
    SentenceEmbeddingError,
    SentenceText,
)


class RecordingEncoder:
    def __init__(self) -> None:
        self.batch_sizes: list[int] = []

    def encode(self, sentences: list[str]) -> list[list[float]]:
        self.batch_sizes.append(len(sentences))
        return [[float(index + 1)] * EMBEDDING_DIMENSIONS for index, _ in enumerate(sentences)]


adapter = RecordingEncoder()
result = EncodeSentenceTexts(adapter, batch_size=2).execute(
    [SentenceText(11, "one"), SentenceText(12, "two"), SentenceText(13, "three")]
)
assert [item.sentence_id for item in result] == [11, 12, 13]
assert adapter.batch_sizes == [2, 1]


class WrongDimensionEncoder:
    def encode(self, sentences: list[str]) -> list[list[float]]:
        return [[0.0] * 2 for _ in sentences]


try:
    EncodeSentenceTexts(WrongDimensionEncoder(), 1).execute([SentenceText(99, "bad")])
except SentenceEmbeddingError as error:
    assert "expected 768" in str(error)
else:
    raise AssertionError("invalid vector dimensions were accepted")
print("ENCODE_SHARED_SMOKE status=success")
PY
```

Expected: `ENCODE_SHARED_SMOKE status=success`.

Extend the same ephemeral probe with focused validator and compatibility cases:

- a count-mismatch encoder returns fewer vectors than inputs;
- a non-finite encoder returns a vector containing `float("nan")`;
- `EncodeSentenceTexts.execute([])` is called;
- `EncodeSentenceTexts(..., batch_size=0)` is called;
- the existing `EmbedSegmentedSentences` is invoked through its unchanged public constructor with a
  fake ordered source and recording repository.

Each invalid shared-service case must raise `SentenceEmbeddingError`. For the valid batch adapter,
assert `execute(None)` forwards `crawl_id=None`, preserves sentence IDs/vectors/model name, performs
one `upsert_for_crawl_url()` for the document, and returns the exact old summary counts. Then run a
count-mismatch document through `EmbedSegmentedSentences` and assert it produces one failure and zero
upsert calls. Print `EMBED_BATCH_COMPAT_SMOKE status=success` only after all assertions pass.

- [ ] **Step 6: Run mandatory formatting and focused static checks**

From the worktree root:

```bash
git status --short -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
make format
git restore --source=HEAD -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
git status --short -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
```

The notebook must be clean before and after. Then run from `backend/`:

```bash
uv run ruff format --check src
uv run ruff check src
uv run mypy src
```

Expected: all commands exit `0`.

- [ ] **Step 7: Commit the shared encoding refactor**

```bash
git add backend/src/information_retrieval/domain/embedding.py backend/src/information_retrieval/application/encode_sentence_texts.py backend/src/information_retrieval/application/embed_segmented_sentences.py
git commit -m "refactor: share validated sentence encoding"
```

---

### Task 3: Add exact max-pair search orchestration

**Files:**

- Create: `backend/src/information_retrieval/domain/search.py`
- Create: `backend/src/information_retrieval/application/search_ports.py`
- Create: `backend/src/information_retrieval/application/search_articles.py`
- Manual verification only; create no test file.

**Interfaces:**

- Consumes:
  `split_article_text(text: str)`,
  `SegmentNormalizedTextParts.execute(...)`,
  `EncodeSentenceTexts.execute(...)`, and
  `ArticleSearchRepository.find_best_articles(query_embedding, model_name, limit)`.
- Produces:
  `SearchArticles.execute(text: str, top_k: int) -> ArticleSearchResult` with distinct articles,
  stable ranks, and the best matched input/article sentence pair.

- [ ] **Step 1: Record the missing search-use-case baseline**

```bash
uv run python -c "from information_retrieval.application.search_articles import SearchArticles"
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 2: Define immutable search errors and values**

Create `domain/search.py` with these exact public fields:

```python
from dataclasses import dataclass


class InvalidSearchQueryError(Exception):
    """Identify client-owned input failures without exposing model or persistence details."""


class SearchUnavailableError(Exception):
    """Collapse model and database availability failures into one safe HTTP-facing category."""


@dataclass(frozen=True, slots=True)
class ArticleSearchCandidate:
    crawl_url_id: int
    title: str | None
    url: str
    cosine_distance: float
    sentence_id: int
    sentence_text: str
    paragraph_num: int
    paragraph_part_num: int
    segment_num: int


@dataclass(frozen=True, slots=True)
class MatchedArticleSentence:
    id: int
    text: str
    paragraph_num: int
    paragraph_part_num: int
    segment_num: int


@dataclass(frozen=True, slots=True)
class RelatedArticle:
    rank: int
    crawl_url_id: int
    title: str | None
    url: str
    score: float
    matched_query_sentence: str
    matched_article_sentence: MatchedArticleSentence


@dataclass(frozen=True, slots=True)
class ArticleSearchResult:
    requested_top_k: int
    query_sentences: list[str]
    articles: list[RelatedArticle]
```

- [ ] **Step 3: Define the application-owned repository port**

Create `application/search_ports.py`:

```python
from typing import Protocol

from information_retrieval.domain.search import ArticleSearchCandidate


class ArticleSearchRepository(Protocol):
    def find_best_articles(
        self,
        query_embedding: list[float],
        model_name: str,
        limit: int,
    ) -> list[ArticleSearchCandidate]:
        """Return one exact best sentence per eligible article in stable score order."""
        ...
```

- [ ] **Step 4: Implement raw-text vectorization and deterministic max-pair ranking**

Create `application/search_articles.py`. Use a private `_ScoredPair` dataclass to retain the
query-sentence index for tie-breaking without leaking it into the response. Import `isfinite` from
`math`, `dataclass`, and `Lock`, plus the Task 1-3 application/domain types. Define:

```python
@dataclass(frozen=True, slots=True)
class _ScoredPair:
    query_index: int
    score: float
    candidate: ArticleSearchCandidate
```

The public service must have this signature and implementation shape:

```python
class SearchArticles:
    def __init__(
        self,
        segment_parts: SegmentNormalizedTextParts,
        encode_sentences: EncodeSentenceTexts,
        repository: ArticleSearchRepository,
        model_name: str,
    ) -> None:
        self._segment_parts = segment_parts
        self._encode_sentences = encode_sentences
        self._repository = repository
        self._model_name = model_name
        self._inference_lock = Lock()

    def execute(self, text: str, top_k: int) -> ArticleSearchResult:
        """Keep model work serialized while releasing the lock before read-only database search."""
        query_text = text.strip()
        if not query_text:
            raise InvalidSearchQueryError("text must not be blank")
        if not 1 <= top_k <= 50:
            raise InvalidSearchQueryError("top_k must be between 1 and 50")

        try:
            split_parts = split_article_text(query_text)
        except ArticlePreprocessingError as error:
            raise InvalidSearchQueryError(str(error)) from error
        if not split_parts:
            raise InvalidSearchQueryError("text has no searchable content after preprocessing")

        try:
            with self._inference_lock:
                segments = self._segment_parts.execute(
                    [
                        NormalizedTextPart(1, part_number, part.normalized_text)
                        for part_number, part in enumerate(split_parts, start=1)
                    ]
                )
                if not segments:
                    raise SearchUnavailableError("segmenter returned no usable query sentence")
                query_sentences = [segment.segmented_text for segment in segments]
                encoded = self._encode_sentences.execute(
                    [
                        SentenceText(query_index, sentence)
                        for query_index, sentence in enumerate(query_sentences)
                    ]
                )
        except SearchUnavailableError:
            raise
        except (ArticleSegmentationError, SentenceEmbeddingError) as error:
            raise SearchUnavailableError("query vectorization failed") from error

        if any(not any(value != 0.0 for value in item.embedding) for item in encoded):
            raise SearchUnavailableError("query vectorization produced a zero vector")

        articles = self._rank_articles(encoded, query_sentences, top_k)
        return ArticleSearchResult(top_k, query_sentences, articles)

    def _rank_articles(
        self,
        encoded: list[EncodedSentence],
        query_sentences: list[str],
        top_k: int,
    ) -> list[RelatedArticle]:
        """Union per-query top-k sets because an omitted article already has k ahead of it."""
        best_by_article: dict[int, _ScoredPair] = {}
        for encoded_sentence in encoded:
            query_index = encoded_sentence.sentence_id
            candidates = self._repository.find_best_articles(
                encoded_sentence.embedding,
                model_name=self._model_name,
                limit=top_k,
            )
            for candidate in candidates:
                if not isfinite(candidate.cosine_distance):
                    raise SearchUnavailableError(
                        "article similarity query returned a non-finite distance"
                    )
                pair = _ScoredPair(
                    query_index=query_index,
                    score=1.0 - candidate.cosine_distance,
                    candidate=candidate,
                )
                current = best_by_article.get(candidate.crawl_url_id)
                pair_key = (-pair.score, pair.query_index, candidate.sentence_id)
                if current is None:
                    best_by_article[candidate.crawl_url_id] = pair
                    continue
                current_key = (
                    -current.score,
                    current.query_index,
                    current.candidate.sentence_id,
                )
                if pair_key < current_key:
                    best_by_article[candidate.crawl_url_id] = pair

        ordered_pairs = sorted(
            best_by_article.values(),
            key=lambda pair: (-pair.score, pair.candidate.crawl_url_id),
        )[:top_k]
        return [
            RelatedArticle(
                rank=rank,
                crawl_url_id=pair.candidate.crawl_url_id,
                title=pair.candidate.title,
                url=pair.candidate.url,
                score=pair.score,
                matched_query_sentence=query_sentences[pair.query_index],
                matched_article_sentence=MatchedArticleSentence(
                    id=pair.candidate.sentence_id,
                    text=pair.candidate.sentence_text,
                    paragraph_num=pair.candidate.paragraph_num,
                    paragraph_part_num=pair.candidate.paragraph_part_num,
                    segment_num=pair.candidate.segment_num,
                ),
            )
            for rank, pair in enumerate(ordered_pairs, start=1)
        ]
```

The repository call must occur after the `with self._inference_lock` block. This is what prevents a
slow database query from blocking another request's model inference slot.

- [ ] **Step 5: Run a manual max-pair/deduplication smoke probe**

Use fake model boundaries and a fake read-only repository, but run the real normalization,
segmentation service, encoding service, and search orchestration:

```bash
uv run python - <<'PY'
from information_retrieval.application.encode_sentence_texts import EncodeSentenceTexts
from information_retrieval.application.search_articles import SearchArticles
from information_retrieval.application.segment_normalized_text_parts import (
    SegmentNormalizedTextParts,
)
from information_retrieval.domain.embedding import EMBEDDING_DIMENSIONS
from information_retrieval.domain.search import ArticleSearchCandidate


class TwoSentenceSegmenter:
    def segment(self, text: str) -> list[str]:
        return [item.strip() for item in text.split(".") if item.strip()]


class IndexedEncoder:
    def encode(self, sentences: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for sentence in sentences:
            vector = [0.0] * EMBEDDING_DIMENSIONS
            vector[0 if "alpha" in sentence else 1] = 1.0
            vectors.append(vector)
        return vectors


class CandidateRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[list[float], str, int]] = []

    def find_best_articles(
        self, query_embedding: list[float], model_name: str, limit: int
    ) -> list[ArticleSearchCandidate]:
        self.calls.append((query_embedding, model_name, limit))
        if query_embedding[0] == 1.0:
            return [
                ArticleSearchCandidate(2, "B", "https://b", 0.10, 20, "b one", 1, 1, 1),
                ArticleSearchCandidate(1, "A", "https://a", 0.20, 10, "a one", 1, 1, 1),
                ArticleSearchCandidate(4, "D", "https://d", 0.25, 40, "d q0", 1, 1, 1),
                ArticleSearchCandidate(6, "F", "https://f", 0.30, 62, "f high id", 1, 1, 1),
                ArticleSearchCandidate(6, "F", "https://f", 0.30, 61, "f low id", 1, 1, 2),
            ][:limit]
        return [
            ArticleSearchCandidate(1, "A", "https://a", 0.05, 11, "a two", 2, 1, 1),
            ArticleSearchCandidate(3, None, "https://c", 0.10, 30, "c one", 1, 1, 1),
            ArticleSearchCandidate(5, "E", "https://e", 0.10, 50, "e one", 1, 1, 1),
            ArticleSearchCandidate(4, "D", "https://d", 0.25, 39, "d q1", 1, 1, 1),
        ][:limit]


repository = CandidateRepository()
service = SearchArticles(
    SegmentNormalizedTextParts(TwoSentenceSegmenter()),
    EncodeSentenceTexts(IndexedEncoder(), batch_size=2),
    repository,
    "vinai/phobert-base",
)
result = service.execute("alpha. beta.", top_k=6)
assert [article.crawl_url_id for article in result.articles] == [1, 2, 3, 5, 4, 6]
assert [round(article.score, 2) for article in result.articles] == [
    0.95,
    0.90,
    0.90,
    0.90,
    0.75,
    0.70,
]
assert result.articles[0].matched_query_sentence == "beta"
assert result.articles[4].matched_query_sentence == "alpha"
assert result.articles[4].matched_article_sentence.id == 40
assert result.articles[5].matched_article_sentence.id == 61
assert len({article.crawl_url_id for article in result.articles}) == 6
assert len(repository.calls) == 2
assert [call[1:] for call in repository.calls] == [
    ("vinai/phobert-base", 6),
    ("vinai/phobert-base", 6),
]
print("SEARCH_APPLICATION_SMOKE status=success")
PY
```

Expected: `SEARCH_APPLICATION_SMOKE status=success`.

- [ ] **Step 6: Run mandatory formatting and focused static checks**

From the worktree root:

```bash
git status --short -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
make format
git restore --source=HEAD -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
git status --short -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
```

The notebook must be clean before and after. Then run from `backend/`:

```bash
uv run ruff format --check src
uv run ruff check src
uv run mypy src
```

Expected: all commands exit `0`.

- [ ] **Step 7: Commit the application search slice**

```bash
git add backend/src/information_retrieval/domain/search.py backend/src/information_retrieval/application/search_ports.py backend/src/information_retrieval/application/search_articles.py
git commit -m "feat: add exact article search use case"
```

---

### Task 4: Implement the exact PostgreSQL cosine repository

**Files:**

- Create: `backend/src/information_retrieval/infrastructure/article_search_repository.py`
- Read only: `backend/src/information_retrieval/infrastructure/database.py:25-199`
- Manual verification only; create no test file and perform no database write.

**Interfaces:**

- Consumes: `CrawlUrlRow`, `ProcessedParagraphRow`, `SegmentedSentenceRow`,
  `SentenceEmbeddingRow`, pgvector's `cosine_distance()`, and
  `ArticleSearchRepository.find_best_articles(...)`.
- Produces:
  `PostgresArticleSearchRepository.find_best_articles(query_embedding: list[float],
model_name: str, limit: int) -> list[ArticleSearchCandidate]`.

- [ ] **Step 1: Record the missing repository baseline**

```bash
uv run python -c "from information_retrieval.infrastructure.article_search_repository import PostgresArticleSearchRepository"
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 2: Build one exact best sentence per article**

Create `infrastructure/article_search_repository.py`. The core statement must follow this shape:

```python
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from information_retrieval.domain.search import (
    ArticleSearchCandidate,
    SearchUnavailableError,
)
from information_retrieval.infrastructure.database import (
    CrawlUrlRow,
    ProcessedParagraphRow,
    SegmentedSentenceRow,
    SentenceEmbeddingRow,
)


class PostgresArticleSearchRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def find_best_articles(
        self,
        query_embedding: list[float],
        model_name: str,
        limit: int,
    ) -> list[ArticleSearchCandidate]:
        """Rank distinct articles inside a read-only transaction before applying the limit."""
        cosine_distance = SentenceEmbeddingRow.embedding.cosine_distance(query_embedding)
        first_title = (
            select(ProcessedParagraphRow.source_text)
            .where(
                ProcessedParagraphRow.crawl_url_id == SegmentedSentenceRow.crawl_url_id,
                ProcessedParagraphRow.block_type == "title",
            )
            .order_by(
                ProcessedParagraphRow.paragraph_num,
                ProcessedParagraphRow.paragraph_part_num,
                ProcessedParagraphRow.id,
            )
            .limit(1)
            .correlate(SegmentedSentenceRow)
            .scalar_subquery()
        )
        per_article = (
            select(
                SegmentedSentenceRow.crawl_url_id.label("crawl_url_id"),
                CrawlUrlRow.url.label("url"),
                first_title.label("title"),
                SegmentedSentenceRow.id.label("sentence_id"),
                SegmentedSentenceRow.segmented_text.label("sentence_text"),
                SegmentedSentenceRow.paragraph_num.label("paragraph_num"),
                SegmentedSentenceRow.paragraph_part_num.label("paragraph_part_num"),
                SegmentedSentenceRow.segment_num.label("segment_num"),
                cosine_distance.label("cosine_distance"),
            )
            .join(
                SentenceEmbeddingRow,
                SentenceEmbeddingRow.segmented_sentence_id == SegmentedSentenceRow.id,
            )
            .join(CrawlUrlRow, CrawlUrlRow.id == SegmentedSentenceRow.crawl_url_id)
            .where(
                SentenceEmbeddingRow.model_name == model_name,
                CrawlUrlRow.status == "completed",
                cosine_distance.is_not(None),
            )
            .distinct(SegmentedSentenceRow.crawl_url_id)
            .order_by(
                SegmentedSentenceRow.crawl_url_id,
                cosine_distance,
                SegmentedSentenceRow.id,
            )
            .subquery()
        )
        statement = (
            select(per_article)
            .order_by(
                per_article.c.cosine_distance,
                per_article.c.crawl_url_id,
                per_article.c.sentence_id,
            )
            .limit(limit)
        )

        try:
            with Session(self._engine) as session:
                session.execute(text("SET TRANSACTION READ ONLY"))
                rows = session.execute(statement).mappings().all()
        except SQLAlchemyError as error:
            raise SearchUnavailableError("article similarity query failed") from error

        return [
            ArticleSearchCandidate(
                crawl_url_id=row["crawl_url_id"],
                title=row["title"],
                url=row["url"],
                cosine_distance=float(row["cosine_distance"]),
                sentence_id=row["sentence_id"],
                sentence_text=row["sentence_text"],
                paragraph_num=row["paragraph_num"],
                paragraph_part_num=row["paragraph_part_num"],
                segment_num=row["segment_num"],
            )
            for row in rows
        ]
```

PostgreSQL emits `DISTINCT ON (crawl_url_id)`: the inner ordering chooses the lowest-distance
sentence and lowest sentence ID for each article, while the outer ordering returns the best distinct
articles. `SET TRANSACTION READ ONLY` makes PostgreSQL reject any accidental write introduced into
this adapter. Do not place `LIMIT` on raw sentence rows.

- [ ] **Step 3: Compile the production SQL without contacting PostgreSQL**

Expose no extra production method. Patch only the repository module's `Session` symbol in an
ephemeral script so `find_best_articles()` builds its real statement without opening a connection,
then compile the captured statement with the PostgreSQL dialect:

```bash
uv run python - <<'PY'
from unittest.mock import patch

from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

from information_retrieval.infrastructure.article_search_repository import (
    PostgresArticleSearchRepository,
)


class EmptyResult:
    def mappings(self) -> "EmptyResult":
        return self

    def all(self) -> list[object]:
        return []


class RecordingSession:
    statements: list[object] = []

    def __init__(self, engine: object) -> None:
        pass

    def __enter__(self) -> "RecordingSession":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def execute(self, statement: object) -> EmptyResult:
        self.statements.append(statement)
        return EmptyResult()


with patch(
    "information_retrieval.infrastructure.article_search_repository.Session",
    RecordingSession,
):
    rows = PostgresArticleSearchRepository(object()).find_best_articles(
        [0.0] * 768,
        "vinai/phobert-base",
        3,
    )

assert rows == []
assert len(RecordingSession.statements) == 2
assert str(RecordingSession.statements[0]) == "SET TRANSACTION READ ONLY"
statement = RecordingSession.statements[1]
sql = str(
    statement.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": False},
    )
)
compiled = statement.compile(dialect=postgresql.dialect())
assert "DISTINCT ON (segmented_sentences.crawl_url_id)" in sql
assert " <=> " in sql
assert "sentence_embeddings.model_name" in sql
assert "crawl_urls.status" in sql
assert "ORDER BY segmented_sentences.crawl_url_id" in sql
assert "ORDER BY anon_1.cosine_distance, anon_1.crawl_url_id" in sql
assert sql.count(" LIMIT ") == 2  # title lookup plus the outer article limit
assert any(isinstance(bind.type, VECTOR) for bind in compiled.binds.values())
print("REPOSITORY_SQL status=success")
PY
```

Expected: `REPOSITORY_SQL status=success`. Also inspect the compiled text for
`segmented_sentences.id` in the inner tie-break and `anon_1.sentence_id` in the outer tie-break. The
two `LIMIT` clauses are intentional: one belongs to the correlated first-title scalar query and one
limits distinct articles; there is no raw-sentence limit.

- [ ] **Step 4: Run a read-only repository smoke against the development corpus**

With the local development PostgreSQL running, execute from `backend/`:

```bash
uv run python - <<'PY'
from sqlalchemy import select
from sqlalchemy.orm import Session

from information_retrieval.infrastructure.article_search_repository import (
    PostgresArticleSearchRepository,
)
from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.database import (
    CrawlUrlRow,
    SegmentedSentenceRow,
    SentenceEmbeddingRow,
    create_database_engine,
)

settings = get_settings()
engine = create_database_engine(settings.database_url)
repository = PostgresArticleSearchRepository(engine)
vector = [0.0] * 768
vector[0] = 1.0
limit = 3
actual = repository.find_best_articles(vector, settings.phobert_model_name, limit)

distance = SentenceEmbeddingRow.embedding.cosine_distance(vector)
with Session(engine) as session:
    raw_rows = session.execute(
        select(
            SegmentedSentenceRow.crawl_url_id,
            SegmentedSentenceRow.id,
            distance,
        )
        .join(
            SentenceEmbeddingRow,
            SentenceEmbeddingRow.segmented_sentence_id == SegmentedSentenceRow.id,
        )
        .join(CrawlUrlRow, CrawlUrlRow.id == SegmentedSentenceRow.crawl_url_id)
        .where(
            SentenceEmbeddingRow.model_name == settings.phobert_model_name,
            CrawlUrlRow.status == "completed",
            distance.is_not(None),
        )
    ).all()

best_by_article: dict[int, tuple[float, int]] = {}
for crawl_url_id, sentence_id, raw_distance in raw_rows:
    candidate_key = (float(raw_distance), sentence_id)
    current = best_by_article.get(crawl_url_id)
    if current is None or candidate_key < current:
        best_by_article[crawl_url_id] = candidate_key
expected = sorted(
    (
        (crawl_url_id, candidate_distance, sentence_id)
        for crawl_url_id, (candidate_distance, sentence_id) in best_by_article.items()
    ),
    key=lambda item: (item[1], item[0]),
)[:limit]
assert expected
assert [
    (row.crawl_url_id, row.cosine_distance, row.sentence_id) for row in actual
] == expected
assert repository.find_best_articles(
    vector,
    "model-that-does-not-exist",
    limit,
) == []
print(
    "REPOSITORY_SMOKE status=success "
    f"eligible_articles={len(best_by_article)} returned={len(actual)}"
)
PY
```

Expected: `REPOSITORY_SMOKE status=success eligible_articles=<positive> returned=3`. This independent
full-sentence scan proves the repository chose the minimum `(distance, sentence_id)` per eligible
completed article, applied the configured model filter, and sorted by `(distance, crawl_url_id)`.

- [ ] **Step 5: Run mandatory formatting and focused static checks**

From the worktree root:

```bash
git status --short -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
make format
git restore --source=HEAD -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
git status --short -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
```

The notebook must be clean before and after. Then run from `backend/`:

```bash
uv run ruff format --check src
uv run ruff check src
uv run mypy src
```

Expected: all commands exit `0`.

- [ ] **Step 6: Commit the read-only exact repository**

```bash
git add backend/src/information_retrieval/infrastructure/article_search_repository.py
git commit -m "feat: query exact article cosine matches"
```

---

### Task 5: Wire the lazy FastAPI search endpoint

**Files:**

- Create: `backend/src/information_retrieval/infrastructure/model_paths.py`
- Create: `backend/src/information_retrieval/presentation/http/routes/search.py`
- Modify: `backend/src/information_retrieval/presentation/cli/segment.py:1-77`
- Modify: `backend/src/information_retrieval/presentation/cli/embed.py:1-60`
- Modify: `backend/src/information_retrieval/presentation/http/dependencies.py:1-38`
- Modify: `backend/src/information_retrieval/presentation/http/schemas.py:1-31`
- Modify: `backend/src/information_retrieval/main.py:7-36`
- Manual verification only; create no test file.

**Interfaces:**

- Consumes: existing settings and engine; Task 1/2 shared services; Task 3 search use case; Task 4
  PostgreSQL repository; existing concrete VnCoreNLP/PhoBERT adapters.
- Produces:
  `get_search_articles_use_case() -> SearchArticles`,
  `POST /api/v1/search/articles`, and the exact approved Pydantic response contract.
- Preserves: app lifespan, health/crawler routes, CORS methods, CLI flags/output/exit codes, and lazy
  absence of torch/transformers from ordinary application import/startup.

- [ ] **Step 1: Record the missing route baseline**

```bash
uv run python -c "from information_retrieval.main import create_app; assert '/api/v1/search/articles' not in {route.path for route in create_app().routes}; print('SEARCH_ROUTE status=missing')"
```

Expected: `SEARCH_ROUTE status=missing`.

- [ ] **Step 2: Centralize backend-relative model paths**

Create `infrastructure/model_paths.py`:

```python
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def resolve_model_dir(configured_path: Path) -> Path:
    """Anchor relative model caches to backend so every entry point loads identical artifacts."""
    if configured_path.is_absolute():
        return configured_path.resolve()
    return (_BACKEND_ROOT / configured_path).resolve()
```

In both CLI modules, remove their private `_BACKEND_ROOT` and `_resolve_model_dir()` definitions,
import `resolve_model_dir`, and replace existing calls. Do not change argparse, lazy VnCoreNLP import,
logs, summaries, or return codes.

- [ ] **Step 3: Add frozen request and response schemas**

Extend `presentation/http/schemas.py` with:

```python
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

SearchText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000),
]


class SearchArticlesRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: SearchText
    top_k: Annotated[int, Field(strict=True, ge=1, le=50)] = 10


class SearchQueryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    segment_count: int
    segmented_sentences: list[str]


class MatchedArticleSentenceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    text: str
    paragraph_num: int
    paragraph_part_num: int
    segment_num: int


class RelatedArticleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    rank: int
    crawl_url_id: int
    title: str | None
    url: str
    score: float
    matched_query_sentence: str
    matched_article_sentence: MatchedArticleSentenceResponse


class SearchArticlesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["success"] = "success"
    top_k: int
    returned_count: int
    query: SearchQueryResponse
    articles: list[RelatedArticleResponse]
```

Merge the import lines rather than duplicating `BaseModel`/`ConfigDict` imports.

- [ ] **Step 4: Build models lazily and exactly once per process**

Extend `presentation/http/dependencies.py` without importing torch, transformers, or py-vncorenlp at
module import time:

```python
from threading import Lock

from sqlalchemy.exc import SQLAlchemyError

from information_retrieval.application.search_articles import SearchArticles
from information_retrieval.domain.embedding import SentenceEmbeddingError
from information_retrieval.domain.search import SearchUnavailableError
from information_retrieval.domain.segmentation import ArticleSegmentationError

_search_build_lock = Lock()


@lru_cache(maxsize=1)
def _build_search_articles_use_case() -> SearchArticles:
    """Load heavy model adapters only after a search request reaches the HTTP boundary."""
    try:
        from information_retrieval.application.encode_sentence_texts import EncodeSentenceTexts
        from information_retrieval.application.segment_normalized_text_parts import (
            SegmentNormalizedTextParts,
        )
        from information_retrieval.infrastructure.article_search_repository import (
            PostgresArticleSearchRepository,
        )
        from information_retrieval.infrastructure.model_paths import resolve_model_dir
        from information_retrieval.infrastructure.phobert_sentence_encoder import (
            PhoBertSentenceEncoder,
        )
        from information_retrieval.infrastructure.vncorenlp_segmenter import VnCoreNlpWordSegmenter

        settings = get_settings()
        segment_parts = SegmentNormalizedTextParts(
            VnCoreNlpWordSegmenter(resolve_model_dir(settings.segmenter_model_dir))
        )
        encode_sentences = EncodeSentenceTexts(
            PhoBertSentenceEncoder(
                model_name=settings.phobert_model_name,
                cache_dir=resolve_model_dir(settings.phobert_model_dir),
                max_length=settings.embedding_max_length,
            ),
            settings.embedding_batch_size,
        )
        return SearchArticles(
            segment_parts=segment_parts,
            encode_sentences=encode_sentences,
            repository=PostgresArticleSearchRepository(get_crawl_engine()),
            model_name=settings.phobert_model_name,
        )
    except (
        ArticleSegmentationError,
        ImportError,
        SentenceEmbeddingError,
        SQLAlchemyError,
        OSError,
        RuntimeError,
        ValueError,
    ) as error:
        raise SearchUnavailableError("search model initialization failed") from error


def get_search_articles_use_case() -> SearchArticles:
    """Serialize the first cache miss so concurrent requests cannot duplicate model memory."""
    with _search_build_lock:
        return _build_search_articles_use_case()
```

Do not inject this builder with `Depends`: the route must call it inside its `try` block so first-load
failures map to the search-specific HTTP 503 instead of bypassing route error handling. Failed
construction is not cached, allowing a later request to retry after model files become available.

- [ ] **Step 5: Add route projection, safe errors, and terminal logs**

Create `presentation/http/routes/search.py` with:

```python
import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException, status

from information_retrieval.domain.search import (
    ArticleSearchResult,
    InvalidSearchQueryError,
    SearchUnavailableError,
)
from information_retrieval.presentation.http.dependencies import (
    get_search_articles_use_case,
)
from information_retrieval.presentation.http.schemas import (
    MatchedArticleSentenceResponse,
    RelatedArticleResponse,
    SearchArticlesRequest,
    SearchArticlesResponse,
    SearchQueryResponse,
)

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger("uvicorn.error")


def _sentence_preview(text: str) -> str:
    """Bound one-line previews so useful matches cannot flood or forge terminal log lines."""
    return " ".join(text.split())[:160]


def _to_response(result: ArticleSearchResult) -> SearchArticlesResponse:
    """Round only at the wire boundary so ranking always uses the full database score."""
    articles = [
        RelatedArticleResponse(
            rank=article.rank,
            crawl_url_id=article.crawl_url_id,
            title=article.title,
            url=article.url,
            score=round(article.score, 6),
            matched_query_sentence=article.matched_query_sentence,
            matched_article_sentence=MatchedArticleSentenceResponse(
                id=article.matched_article_sentence.id,
                text=article.matched_article_sentence.text,
                paragraph_num=article.matched_article_sentence.paragraph_num,
                paragraph_part_num=article.matched_article_sentence.paragraph_part_num,
                segment_num=article.matched_article_sentence.segment_num,
            ),
        )
        for article in result.articles
    ]
    return SearchArticlesResponse(
        top_k=result.requested_top_k,
        returned_count=len(articles),
        query=SearchQueryResponse(
            segment_count=len(result.query_sentences),
            segmented_sentences=result.query_sentences,
        ),
        articles=articles,
    )
```

Add the handler:

```python
@router.post("/articles", response_model=SearchArticlesResponse)
def search_articles(request: SearchArticlesRequest) -> SearchArticlesResponse:
    """Keep search failures local so crawler and health response contracts remain untouched."""
    started_at = perf_counter()
    try:
        result = get_search_articles_use_case().execute(request.text, request.top_k)
    except InvalidSearchQueryError as error:
        logger.warning('SEARCH status=failed category=validation reason="%s"', error)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except SearchUnavailableError as error:
        logger.error(
            'SEARCH status=failed category=unavailable reason="%s"',
            error,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is temporarily unavailable",
        ) from error

    response = _to_response(result)
    duration_ms = round((perf_counter() - started_at) * 1000)
    logger.info(
        "SEARCH status=success query_segments=%d requested_top_k=%d returned=%d duration_ms=%d",
        response.query.segment_count,
        response.top_k,
        response.returned_count,
        duration_ms,
    )
    for article in response.articles:
        logger.info(
            'SEARCH_RESULT rank=%d crawl_url_id=%d score=%.6f sentence_id=%d url="%s" preview="%s"',
            article.rank,
            article.crawl_url_id,
            article.score,
            article.matched_article_sentence.id,
            _sentence_preview(article.url),
            _sentence_preview(article.matched_article_sentence.text),
        )
    return response
```

Do not log request text, vectors, token IDs, masks, database URLs, or model paths in success records.

- [ ] **Step 6: Mount the router without changing startup behavior**

Import the new router in `main.py`:

```python
from information_retrieval.presentation.http.routes.search import router as search_router
```

Then add only:

```python
app.include_router(search_router, prefix="/api/v1")
```

Do not call `get_search_articles_use_case()` from `create_app()` or `_lifespan()`.

- [ ] **Step 7: Verify request validation and lazy imports without model/DB access**

Run this probe from `backend/`:

```bash
uv run python - <<'PY'
import sys

from pydantic import ValidationError

from information_retrieval.main import create_app
from information_retrieval.presentation.http.schemas import SearchArticlesRequest

request = SearchArticlesRequest(text="  nội dung  ")
assert request.text == "nội dung"
assert request.top_k == 10
for payload in (
    {"text": "   ", "top_k": 10},
    {"text": "valid", "top_k": 0},
    {"text": "valid", "top_k": 51},
    {"text": "valid", "top_k": True},
    {"text": "valid", "top_k": "10"},
    {"text": "valid", "top_k": 10.0},
    {"text": "x" * 10_001, "top_k": 10},
):
    try:
        SearchArticlesRequest(**payload)
    except ValidationError:
        pass
    else:
        raise AssertionError(f"invalid request was accepted: {payload}")

app = create_app()
assert "/api/v1/search/articles" in {route.path for route in app.routes}
assert "torch" not in sys.modules
assert "transformers" not in sys.modules
assert "py_vncorenlp" not in sys.modules
print("SEARCH_HTTP_IMPORT_SMOKE status=success")
PY
```

Expected: `SEARCH_HTTP_IMPORT_SMOKE status=success` without loading Java or PhoBERT.

- [ ] **Step 8: Run mandatory formatting and focused static checks**

From the worktree root:

```bash
git status --short -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
make format
git restore --source=HEAD -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
git status --short -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
```

The notebook must be clean before and after. Then run from `backend/`:

```bash
uv run ruff format --check src
uv run ruff check src
uv run mypy src
```

Expected: all commands exit `0`.

- [ ] **Step 9: Commit the HTTP slice and shared path resolver**

```bash
git add backend/src/information_retrieval/infrastructure/model_paths.py backend/src/information_retrieval/presentation/cli/segment.py backend/src/information_retrieval/presentation/cli/embed.py backend/src/information_retrieval/presentation/http/dependencies.py backend/src/information_retrieval/presentation/http/schemas.py backend/src/information_retrieval/presentation/http/routes/search.py backend/src/information_retrieval/main.py
git commit -m "feat: expose semantic article search API"
```

---

### Task 6: Document and verify the complete feature

**Files:**

- Modify: `backend/.env.example:1-8`
- Modify: `README.md:21-137`
- Read only: every production file changed in Tasks 1-5.
- Manual verification only; create no test file.

**Interfaces:**

- Consumes: completed endpoint and the local development PostgreSQL/model caches.
- Produces: documented environment keys, curl examples, live proof for one- and multi-sentence
  search, deterministic exact ranking, validation errors, no-write behavior, and old-route startup.

- [ ] **Step 1: Document existing model settings**

Append these already-supported keys to `backend/.env.example` without changing defaults:

```dotenv
APP_PHOBERT_MODEL_NAME=vinai/phobert-base
APP_PHOBERT_MODEL_DIR=data/models/vinai-phobert
APP_EMBEDDING_BATCH_SIZE=16
APP_EMBEDDING_MAX_LENGTH=256
```

- [ ] **Step 2: Add a focused README section**

After the preprocessing pipeline section, document in Vietnamese to match the existing README:

- `make embed`/`make embed CRAWL_ID=<id>` as the corpus prerequisite;
- request fields `text` and `top_k` with limits/defaults;
- one curl example for `POST /api/v1/search/articles`;
- response fields, distinct-article semantics, exact max-pair cosine score, and stable sorting;
- HTTP 422/503/empty-200 behavior;
- lazy first-request model load and one model copy per Uvicorn process;
- query/transient data and the absence of database writes;
- terminal `SEARCH`/`SEARCH_RESULT` output and sensitive data excluded from logs.

Use this curl example verbatim:

```bash
curl -sS -X POST http://localhost:8000/api/v1/search/articles \
  -H 'Content-Type: application/json' \
  -d '{"text":"Giá vé máy bay đi Singapore giảm mạnh.","top_k":10}'
```

- [ ] **Step 3: Run project formatting while preserving the known notebook baseline**

First confirm the notebook is clean before formatting:

```bash
git status --short -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
```

Expected: no output. From the worktree root run:

```bash
make format
```

Inspect changed paths. Ruff is expected to touch the unrelated baseline notebook. After confirming
that this task did not modify it before `make format`, discard only that formatter-generated change:

```bash
git restore --source=HEAD -- backend/notebook/analysisData/analyze_txt_corpus.ipynb
```

Then confirm all remaining changes are scoped to Tasks 1-6:

```bash
git status --short
git diff --check
```

- [ ] **Step 4: Run full and scoped static verification**

Run from the worktree root:

```bash
make verify
```

Expected baseline result: `make verify` stops nonzero at Ruff formatting because
`backend/notebook/analysisData/analyze_txt_corpus.ipynb` would be reformatted. If lint is invoked
independently on the whole backend, the same notebook also has the two known baseline findings
`I001` and `UP045`. Do not describe repository-wide verification as green.

Run the scoped commands separately. Use `backend/` as the working directory for the first three:

```bash
uv run ruff format --check src
uv run ruff check src
uv run mypy src
```

Use `ui/` as the working directory for the next four:

```bash
npm run format:check
npm run lint
npm run typecheck
npm run build
```

Return to the worktree root for the final two:

```bash
docker compose config --quiet
git diff --check
```

Expected: every scoped command exits `0`.

- [ ] **Step 5: Prove model failure is route-local and retryable**

Create an empty temporary model directory and start a separate Uvicorn process from `backend/` on
port `8002`. This exercises the real lazy builder without touching the working model cache:

```bash
SEARCH_EMPTY_MODEL_DIR=$(mktemp -d /private/tmp/semantic-search-empty-models.XXXXXX)
APP_DATABASE_URL=postgresql+psycopg://information_retrieval:information_retrieval@localhost:54322/information_retrieval \
APP_SEGMENTER_MODEL_DIR="$SEARCH_EMPTY_MODEL_DIR" \
APP_PHOBERT_MODEL_DIR="$SEARCH_EMPTY_MODEL_DIR" \
uv run uvicorn information_retrieval.main:create_app --factory --host 127.0.0.1 --port 8002
```

From another terminal, call health, search, then health again:

```bash
curl -sS http://127.0.0.1:8002/api/v1/health
curl -sS -o /private/tmp/search-unavailable.json -w '%{http_code}\n' -X POST http://127.0.0.1:8002/api/v1/search/articles -H 'Content-Type: application/json' -d '{"text":"nội dung hợp lệ","top_k":3}'
jq -e '.detail == "Search service is temporarily unavailable"' /private/tmp/search-unavailable.json
curl -sS http://127.0.0.1:8002/api/v1/health
```

Expected: health is `200` before and after, search prints `503`, and the body contains only the
generic detail. The terminal log contains a sanitized `SEARCH status=failed` record but no traceback,
vector, token, database URL, or model path. Stop this Uvicorn process with `Ctrl-C`, then remove only
the empty temporary directory created above:

```bash
rmdir "$SEARCH_EMPTY_MODEL_DIR"
```

- [ ] **Step 6: Start the real API from the isolated worktree**

The ignored model caches live in the main checkout, while this worktree uses the same development
PostgreSQL on `localhost:54322`. Start Uvicorn from `backend/` on port `8001`:

```bash
APP_DATABASE_URL=postgresql+psycopg://information_retrieval:information_retrieval@localhost:54322/information_retrieval \
APP_SEGMENTER_MODEL_DIR=/Users/thangtran/Workplace/master_s_degree/information_retrieval/backend/data/models/py_vncorenlp \
APP_PHOBERT_MODEL_DIR=/Users/thangtran/Workplace/master_s_degree/information_retrieval/backend/data/models/vinai-phobert \
uv run uvicorn information_retrieval.main:create_app --factory --host 127.0.0.1 --port 8001
```

Expected: application startup succeeds before the search models load. Keep this terminal visible for
the log checks below.

- [ ] **Step 7: Snapshot data, then smoke health, one-sentence search, and logs**

After Uvicorn startup has completed but before the first search, run from `backend/` with the exact
same database URL. The inner per-row hashes keep the aggregate bounded while including every column,
including stored vectors:

```bash
APP_DATABASE_URL=postgresql+psycopg://information_retrieval:information_retrieval@localhost:54322/information_retrieval \
uv run python - <<'PY' > /private/tmp/semantic-search-db-before.txt
from sqlalchemy import text
from sqlalchemy.orm import Session

from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.database import create_database_engine

snapshot = text("""
SELECT 'crawl_urls', count(*),
       md5(coalesce(string_agg(md5(row_to_json(c)::text), '' ORDER BY c.id), ''))
FROM crawl_urls AS c
UNION ALL
SELECT 'processed_paragraphs', count(*),
       md5(coalesce(string_agg(md5(row_to_json(p)::text), '' ORDER BY p.id), ''))
FROM processed_paragraphs AS p
UNION ALL
SELECT 'segmented_sentences', count(*),
       md5(coalesce(string_agg(md5(row_to_json(s)::text), '' ORDER BY s.id), ''))
FROM segmented_sentences AS s
UNION ALL
SELECT 'sentence_embeddings', count(*),
       md5(coalesce(string_agg(md5(row_to_json(e)::text), '' ORDER BY e.segmented_sentence_id), ''))
FROM sentence_embeddings AS e
""")
with Session(create_database_engine(get_settings().database_url)) as session:
    for row in session.execute(snapshot):
        print(*row)
PY
```

In another terminal:

```bash
curl -sS http://127.0.0.1:8001/api/v1/health
```

Expected: the existing health response retains `status`, `service`, and `environment`.

```bash
curl -sS -X POST http://127.0.0.1:8001/api/v1/search/articles \
  -H 'Content-Type: application/json' \
  -d '{"text":"Giá vé máy bay đi Singapore giảm mạnh.","top_k":10}' \
  -o /private/tmp/semantic-search-one.json
```

Validate the contract:

```bash
jq -e '.status == "success" and .top_k == 10 and .returned_count == (.articles | length) and .returned_count <= .top_k' /private/tmp/semantic-search-one.json
jq -e '.query.segment_count == (.query.segmented_sentences | length) and .query.segment_count >= 1' /private/tmp/semantic-search-one.json
jq -e '[.articles[].rank] == [range(1; .returned_count + 1)]' /private/tmp/semantic-search-one.json
jq -e '([.articles[].crawl_url_id] | length) == ([.articles[].crawl_url_id] | unique | length)' /private/tmp/semantic-search-one.json
jq -e '[.articles[].score] as $scores | $scores == ($scores | sort | reverse)' /private/tmp/semantic-search-one.json
```

Expected: all `jq -e` commands exit `0`. The Uvicorn terminal contains one `SEARCH` summary and one
`SEARCH_RESULT` per returned article, with no vector/token/mask output.

- [ ] **Step 8: Smoke a multi-sentence query and deterministic repeat**

```bash
curl -sS -X POST http://127.0.0.1:8001/api/v1/search/articles \
  -H 'Content-Type: application/json' \
  -d '{"text":"Giá vé máy bay giảm mạnh. Nhiều hãng hàng không mở thêm chuyến.","top_k":5}' \
  -o /private/tmp/semantic-search-multi-a.json
```

```bash
curl -sS -X POST http://127.0.0.1:8001/api/v1/search/articles \
  -H 'Content-Type: application/json' \
  -d '{"text":"Giá vé máy bay giảm mạnh. Nhiều hãng hàng không mở thêm chuyến.","top_k":5}' \
  -o /private/tmp/semantic-search-multi-b.json
```

```bash
jq -e '.query.segment_count >= 2 and .query.segment_count == (.query.segmented_sentences | length) and .returned_count == (.articles | length) and .returned_count <= 5' /private/tmp/semantic-search-multi-a.json
diff -u /private/tmp/semantic-search-multi-a.json /private/tmp/semantic-search-multi-b.json
```

Expected: the `jq` assertion exits `0` and `diff` produces no output.

- [ ] **Step 9: Independently prove global max-pair top-k semantics**

From `backend/`, re-encode every segmented query sentence returned by the multi-sentence response,
scan every eligible stored sentence for every query vector, reduce in Python by the approved
`(-score, query_index, sentence_id)` key, and compare the global order with the API. This verification
does not call `SearchArticles` or `PostgresArticleSearchRepository`:

```bash
APP_DATABASE_URL=postgresql+psycopg://information_retrieval:information_retrieval@localhost:54322/information_retrieval \
APP_PHOBERT_MODEL_DIR=/Users/thangtran/Workplace/master_s_degree/information_retrieval/backend/data/models/vinai-phobert \
uv run python - <<'PY'
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.database import (
    CrawlUrlRow,
    SegmentedSentenceRow,
    SentenceEmbeddingRow,
    create_database_engine,
)
from information_retrieval.infrastructure.model_paths import resolve_model_dir
from information_retrieval.infrastructure.phobert_sentence_encoder import PhoBertSentenceEncoder

with open("/private/tmp/semantic-search-multi-a.json", encoding="utf-8") as response_file:
    response = json.load(response_file)

settings = get_settings()
query_sentences = response["query"]["segmented_sentences"]
query_vectors = PhoBertSentenceEncoder(
    settings.phobert_model_name,
    resolve_model_dir(settings.phobert_model_dir),
    settings.embedding_max_length,
).encode(query_sentences)

best_by_article: dict[int, tuple[tuple[float, int, int], float]] = {}
with Session(create_database_engine(settings.database_url)) as session:
    for query_index, query_vector in enumerate(query_vectors):
        distance = SentenceEmbeddingRow.embedding.cosine_distance(query_vector)
        rows = session.execute(
            select(
                SegmentedSentenceRow.crawl_url_id,
                SegmentedSentenceRow.id,
                distance,
            )
            .join(
                SentenceEmbeddingRow,
                SentenceEmbeddingRow.segmented_sentence_id == SegmentedSentenceRow.id,
            )
            .join(CrawlUrlRow, CrawlUrlRow.id == SegmentedSentenceRow.crawl_url_id)
            .where(
                SentenceEmbeddingRow.model_name == settings.phobert_model_name,
                CrawlUrlRow.status == "completed",
                distance.is_not(None),
            )
        ).all()
        for crawl_url_id, sentence_id, raw_distance in rows:
            score = 1.0 - float(raw_distance)
            pair_key = (-score, query_index, sentence_id)
            current = best_by_article.get(crawl_url_id)
            if current is None or pair_key < current[0]:
                best_by_article[crawl_url_id] = (pair_key, score)

expected = sorted(
    best_by_article.items(),
    key=lambda item: (item[1][0][0], item[0]),
)[: response["top_k"]]
assert expected
assert len(response["articles"]) == len(expected)
for actual, (crawl_url_id, (pair_key, raw_score)) in zip(
    response["articles"],
    expected,
    strict=True,
):
    query_index = pair_key[1]
    sentence_id = pair_key[2]
    assert actual["crawl_url_id"] == crawl_url_id
    assert actual["matched_article_sentence"]["id"] == sentence_id
    assert actual["matched_query_sentence"] == query_sentences[query_index]
    assert abs(actual["score"] - round(raw_score, 6)) <= 0.00000051

print(
    "MAX_PAIR_CHECK status=success "
    f"query_segments={len(query_vectors)} articles={len(expected)}"
)
PY
```

Expected: `MAX_PAIR_CHECK status=success`. This proves the returned article IDs, matched query
sentences, stored sentence IDs, raw max-pair scores, query-index tie-break, sentence-ID tie-break,
and final crawl-ID order against the full eligible corpus rather than merely recomputing one selected
pair.

- [ ] **Step 10: Verify validation statuses**

```bash
curl -sS -o /private/tmp/search-blank.json -w '%{http_code}\n' -X POST http://127.0.0.1:8001/api/v1/search/articles -H 'Content-Type: application/json' -d '{"text":"   ","top_k":10}'
curl -sS -o /private/tmp/search-normalized-empty.json -w '%{http_code}\n' -X POST http://127.0.0.1:8001/api/v1/search/articles -H 'Content-Type: application/json' -d '{"text":"&gt;\u200b","top_k":10}'
curl -sS -o /private/tmp/search-low-k.json -w '%{http_code}\n' -X POST http://127.0.0.1:8001/api/v1/search/articles -H 'Content-Type: application/json' -d '{"text":"valid","top_k":0}'
curl -sS -o /private/tmp/search-high-k.json -w '%{http_code}\n' -X POST http://127.0.0.1:8001/api/v1/search/articles -H 'Content-Type: application/json' -d '{"text":"valid","top_k":51}'
curl -sS -o /private/tmp/search-bool-k.json -w '%{http_code}\n' -X POST http://127.0.0.1:8001/api/v1/search/articles -H 'Content-Type: application/json' -d '{"text":"valid","top_k":true}'
curl -sS -o /private/tmp/search-string-k.json -w '%{http_code}\n' -X POST http://127.0.0.1:8001/api/v1/search/articles -H 'Content-Type: application/json' -d '{"text":"valid","top_k":"10"}'
curl -sS -o /private/tmp/search-float-k.json -w '%{http_code}\n' -X POST http://127.0.0.1:8001/api/v1/search/articles -H 'Content-Type: application/json' -d '{"text":"valid","top_k":10.0}'
```

Expected: each command prints `422`; the normalized-empty case proves API preprocessing is reused
after Pydantic's nonblank check. From `backend/`, generate a 10,001-character JSON request in a
temporary file, then post that file:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

Path("/private/tmp/search-oversized-request.json").write_text(
    json.dumps({"text": "x" * 10_001, "top_k": 10}),
    encoding="utf-8",
)
PY
```

```bash
curl -sS -o /private/tmp/search-oversized.json -w '%{http_code}\n' -X POST http://127.0.0.1:8001/api/v1/search/articles -H 'Content-Type: application/json' --data-binary @/private/tmp/search-oversized-request.json
```

Expected: `422`.

- [ ] **Step 11: Prove the API search path performed no writes**

The production repository already starts each similarity query with `SET TRANSACTION READ ONLY`, so
PostgreSQL would reject an accidental insert/update/delete in that adapter. As an independent
end-to-end check, repeat the exact Step 7 full-row fingerprint from `backend/` into another file:

```bash
APP_DATABASE_URL=postgresql+psycopg://information_retrieval:information_retrieval@localhost:54322/information_retrieval \
uv run python - <<'PY' > /private/tmp/semantic-search-db-after.txt
from sqlalchemy import text
from sqlalchemy.orm import Session

from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.database import create_database_engine

snapshot = text("""
SELECT 'crawl_urls', count(*),
       md5(coalesce(string_agg(md5(row_to_json(c)::text), '' ORDER BY c.id), ''))
FROM crawl_urls AS c
UNION ALL
SELECT 'processed_paragraphs', count(*),
       md5(coalesce(string_agg(md5(row_to_json(p)::text), '' ORDER BY p.id), ''))
FROM processed_paragraphs AS p
UNION ALL
SELECT 'segmented_sentences', count(*),
       md5(coalesce(string_agg(md5(row_to_json(s)::text), '' ORDER BY s.id), ''))
FROM segmented_sentences AS s
UNION ALL
SELECT 'sentence_embeddings', count(*),
       md5(coalesce(string_agg(md5(row_to_json(e)::text), '' ORDER BY e.segmented_sentence_id), ''))
FROM sentence_embeddings AS e
""")
with Session(create_database_engine(get_settings().database_url)) as session:
    for row in session.execute(snapshot):
        print(*row)
PY
```

```bash
diff -u /private/tmp/semantic-search-db-before.txt /private/tmp/semantic-search-db-after.txt
```

Expected: no output. Matching counts and hashes proves no column in any corpus/search table changed
between post-startup and post-search snapshots. Stop Uvicorn with `Ctrl-C` after collecting terminal
logs.

- [ ] **Step 12: Review scope and commit documentation**

```bash
git status --short
git diff --stat
git diff --check
git diff -- backend/.env.example README.md
```

Confirm no UI, notebook, schema, lockfile, dependency, or unrelated file appears. Then commit:

```bash
git add backend/.env.example README.md
git commit -m "docs: document semantic article search"
```

- [ ] **Step 13: Record final branch evidence**

```bash
git status --short --branch
git log --oneline --decorate main..HEAD
```

Expected: clean `codex/semantic-article-search-api` worktree with the design/plan commits plus the six
implementation commits from this plan. Report repository-wide `make verify` as baseline-blocked,
then separately report the green scoped checks and live search evidence.
