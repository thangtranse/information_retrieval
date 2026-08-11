# Normalize-only Preprocessing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm `--normalize-only` để lưu normalized text với empty segmentation mà không import/load VnCoreNLP, đồng thời thay mọi dấu `-`, `–`, `—` bằng khoảng trắng.

**Architecture:** Domain định nghĩa processing mode và normalization contract. Application use case quyết định có gọi optional segmenter hay lưu `[]`; presentation CLI lazy-import VnCoreNLP chỉ cho download/full mode. Database schema và repository không đổi.

**Tech Stack:** Python 3.14, uv, argparse, SQLAlchemy/PostgreSQL JSONB, Ruff, mypy.

## Global Constraints

- Thực hiện theo `docs/superpowers/specs/2026-08-11-normalize-only-preprocessing-design.md`.
- Không thêm automated tests; dùng inline smoke checks và static verification.
- Không sửa notebook PhoBERT có baseline Ruff format failure.
- Hành vi mặc định của `make preprocess` vẫn normalize rồi segment.
- Function/method business logic phải có WHY docstring/comment.

---

### Task 1: Normalization and application mode

**Files:**
- Modify: `backend/src/information_retrieval/domain/preprocessing.py`
- Modify: `backend/src/information_retrieval/application/preprocess_crawled_articles.py`

**Interfaces:**
- Produces: `PreprocessingMode = Literal["normalize_and_segment", "normalize_only"]`.
- Produces: `PreprocessCrawledArticles(..., segmenter: WordSegmenter | None)`.
- Produces: `execute(crawl_id: int | None = None, mode: PreprocessingMode = "normalize_and_segment") -> PreprocessingSummary`.

- [ ] **Step 1: Capture the current dash behavior with a read-only smoke command**

```bash
cd backend
uv run python -c 'from information_retrieval.domain.preprocessing import normalize_article_text; values = [normalize_article_text(value) for value in ["A-B", "A – B", "2027—2028"]]; print(values); assert values != ["A B", "A B", "2027 2028"]'
```

Expected before implementation: exits `0` and shows ASCII hyphens remain.

- [ ] **Step 2: Change dash mapping and add the mode type**

In `domain/preprocessing.py`, import `Literal`, declare:

```python
PreprocessingMode = Literal["normalize_and_segment", "normalize_only"]
```

Change the dash entries in `CHAR_MAP` to:

```python
"-": " ",
"–": " ",
"—": " ",
```

Keep whitespace collapse after CHAR_MAP so multiple surrounding spaces become one.

- [ ] **Step 3: Make segmentation explicitly mode-dependent**

Change the use case constructor to accept `segmenter: WordSegmenter | None`. Change `execute` to:

```python
def execute(
    self,
    crawl_id: int | None = None,
    mode: PreprocessingMode = "normalize_and_segment",
) -> PreprocessingSummary:
```

Before reading rows, reject full mode without a segmenter:

```python
if mode == "normalize_and_segment" and self._segmenter is None:
    raise ArticlePreprocessingError("word segmenter is required for normalize_and_segment mode")
```

For each paragraph:

```python
if mode == "normalize_only":
    segmented_sentences: list[str] = []
else:
    assert self._segmenter is not None
    segmented_sentences = self._segmenter.segment(normalized_text)
    if not segmented_sentences:
        raise ArticlePreprocessingError(
            f"no segmented sentences at paragraph num {source.num}"
        )
```

- [ ] **Step 4: Verify normalization and static types**

```bash
cd backend
uv run ruff format src/information_retrieval/domain/preprocessing.py src/information_retrieval/application/preprocess_crawled_articles.py
uv run ruff check src/information_retrieval/domain/preprocessing.py src/information_retrieval/application/preprocess_crawled_articles.py
uv run mypy src
uv run python -c 'from information_retrieval.domain.preprocessing import normalize_article_text; values = [normalize_article_text(value) for value in ["A-B", "A – B", "2027—2028"]]; print(values); assert values == ["A B", "A B", "2027 2028"]'
```

Expected: Ruff/mypy pass and the smoke assertion exits `0`.

---

### Task 2: CLI mode and lazy VnCoreNLP import

**Files:**
- Modify: `backend/src/information_retrieval/presentation/cli/preprocess.py`

**Interfaces:**
- Consumes: Task 1 `PreprocessingMode` and optional segmenter constructor.
- Produces: CLI flag `--normalize-only`.

- [ ] **Step 1: Add argument and mutual exclusion**

Add:

```python
parser.add_argument(
    "--normalize-only",
    action="store_true",
    help="normalize source text and store empty segmented_sentences without VnCoreNLP",
)
```

Reject `--download-model-only --normalize-only` with:

```python
if args.download_model_only and args.normalize_only:
    parser.error("--normalize-only cannot be combined with --download-model-only")
```

Keep the existing download + crawl-id conflict.

- [ ] **Step 2: Lazy-import the VnCoreNLP adapter**

Remove the module-level `VnCoreNlpWordSegmenter` import. Add:

Add `from __future__ import annotations`, then define:

```python
def _load_vncorenlp_adapter() -> type[VnCoreNlpWordSegmenter]:
    """Delay Java-backed imports so normalize-only has no model/runtime dependency."""
    from information_retrieval.infrastructure.vncorenlp_segmenter import (
        VnCoreNlpWordSegmenter,
    )

    return VnCoreNlpWordSegmenter
```

Use `TYPE_CHECKING` for the return annotation without importing at runtime. Invoke this loader only
inside download-only and full-mode branches.

- [ ] **Step 3: Build mode-specific dependencies**

Resolve the model path only for download/full mode. For processing:

```python
mode: PreprocessingMode = "normalize_only" if args.normalize_only else "normalize_and_segment"
segmenter: WordSegmenter | None = None
if mode == "normalize_and_segment":
    adapter = _load_vncorenlp_adapter()
    try:
        segmenter = adapter(_resolve_model_dir(settings.segmenter_model_dir))
    except ArticlePreprocessingError as error:
        print(f'PREPROCESS status=failed reason="{error}"', file=sys.stderr)
        return 1
```

Pass `segmenter` into the use case and call `execute(args.crawl_id, mode)`.

- [ ] **Step 4: Verify CLI parsing without database mutation**

```bash
cd backend
uv run python -m information_retrieval.presentation.cli.preprocess --help
uv run python -m information_retrieval.presentation.cli.preprocess --download-model-only --normalize-only
```

Expected: help contains `--normalize-only`; invalid combination exits `2` with the exact mutual
exclusion message.

---

### Task 3: Documentation and end-to-end verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Documents: `make preprocess ARGS=--normalize-only` and focused crawl-id usage.

- [ ] **Step 1: Document normalize-only commands and persistence behavior**

Add:

```bash
make preprocess ARGS=--normalize-only
make preprocess ARGS="--normalize-only --crawl-id=261"
```

Explain that normalize-only neither loads VnCoreNLP nor requires a model cache, maps all dash
characters to spaces, and deliberately replaces prior segmentation with JSONB `[]`.

- [ ] **Step 2: Run normalize-only end-to-end**

```bash
make preprocess ARGS="--normalize-only --crawl-id=1000"
```

Expected: `SUMMARY selected=1 processed=1 paragraphs=11 failed=0`; output has no VnCoreNLP loading
line. Query PostgreSQL and expect `BOOL_AND(segmented_sentences = '[]'::jsonb)` to be true and
`BOOL_AND(normalized_text NOT LIKE '%-%')` to be true.

- [ ] **Step 3: Restore and verify full mode**

```bash
make preprocess ARGS=--crawl-id=1000
```

Expected: VnCoreNLP loads; summary reports one successful document; PostgreSQL
`BOOL_AND(jsonb_array_length(segmented_sentences) > 0)` is true.

- [ ] **Step 4: Run focused repository verification**

```bash
cd backend
uv run ruff format --check src
uv run ruff check src
uv run mypy src
cd ../ui
npm run format:check
npm run lint
npm run typecheck
npm run build
cd ..
docker compose config --quiet
git diff --check
git status --short
```

Expected: focused checks pass; only intentional feature/spec/plan changes appear. Full
`make verify` is not used because its known notebook formatting baseline is outside this scope.

- [ ] **Step 5: Commit implementation**

```bash
git add backend/src/information_retrieval/domain/preprocessing.py backend/src/information_retrieval/application/preprocess_crawled_articles.py backend/src/information_retrieval/presentation/cli/preprocess.py README.md docs/superpowers/plans/2026-08-11-normalize-only-preprocessing.md
git commit -m "feat: add normalize-only preprocessing mode"
```
