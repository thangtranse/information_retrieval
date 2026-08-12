# Semantic Article Search API Design

## Status

Approved in conversation on 2026-08-12.

The approved v1 decisions are:

- `top_k` counts distinct articles, not matching sentences.
- An article score is the maximum cosine similarity over every input-sentence and
  article-sentence pair.
- Retrieval is exact for v1. HNSW/ANN retrieval and document-level embeddings are outside scope.

## Goal

Add `POST /api/v1/search/articles`. The endpoint accepts Vietnamese text, reuses the production
normalization, VnCoreNLP word-segmentation, and PhoBERT sentence-encoding behavior, and returns a
deterministically sorted list of related articles from the existing pgvector corpus.

The implementation must preserve `make preprocess`, `make segment`, `make embed`, health, and
crawler behavior. Query text and query embeddings remain transient and are never persisted.

## Non-goals

- No UI work.
- No HNSW or other approximate-nearest-neighbor query path in v1.
- No document-level embedding table or backfill.
- No similarity threshold; v1 returns up to the requested number of articles.
- No new authentication, rate limiting, migration framework, or automated test suite.
- No token IDs, attention masks, or 768-dimensional vectors in the HTTP response or logs.

## Current pipeline to preserve

The current batch path is intentionally split into three steps:

1. `make preprocess` reads completed crawl artifacts, calls `split_article_text()`, and stores
   normalized parts in `processed_paragraphs`.
2. `make segment` loads VnCoreNLP, validates the 200-normalized-word invariant, segments each part,
   and transactionally replaces the document snapshot in `segmented_sentences`.
3. `make embed` tokenizes segmented sentences with `vinai/phobert-base`, mean-pools non-padding,
   non-special token states, validates 768-dimensional finite output, and upserts one vector per
   segmented sentence in `sentence_embeddings`.

The API must call the same text-processing and model boundaries without entering the batch
repositories. Calling the API must not create, replace, or delete crawl, paragraph, sentence, or
embedding rows.

## Architecture

The feature is a separate backend vertical slice:

- Domain types describe a normalized query part, a request-local segmented query sentence, and a
  ranked article match.
- Application services own reusable segmentation, reusable sentence-vector validation, and the
  search orchestration.
- Infrastructure adapters continue to own VnCoreNLP, PhoBERT, and PostgreSQL/pgvector behavior.
- The HTTP layer owns request validation, response projection, dependency composition, and
  search-specific error-to-status mapping.

Dependencies continue to point inward. Domain and application code must not import FastAPI,
SQLAlchemy, transformers, torch, or py-vncorenlp.

### Focused refactors instead of duplicate processing

The existing private segmentation behavior in
`SegmentProcessedParagraphs._segment_document()` will be extracted into a persistence-neutral
application service. It accepts ordered normalized parts and returns ordered request-independent
segments. It retains all existing invariants:

- Validate every part against `MAX_PARAGRAPH_WORDS` before the first model call.
- Preserve part ordering.
- Reset `segment_num` to one for each part.
- Reject empty or whitespace-only model output.
- Preserve the segment text returned by the adapter.
- Raise the existing `ArticleSegmentationError` category.

`SegmentProcessedParagraphs` will map stored paragraphs into this shared service, enrich the
results with the existing database metadata, and persist them exactly as it does now. The search
use case will map `split_article_text()` output into the same service without inventing crawl or
database identifiers.

The existing batching and output-validation logic in `EmbedSegmentedSentences` will likewise be
extracted into a reusable sentence-text encoder service. Both batch embedding and search must use
the same existing rules for positive batch size, result count, 768 dimensions, finite values, and
nonempty output. Search additionally rejects an all-zero query vector before cosine retrieval;
this query-only invariant does not tighten or otherwise change `make embed`. The concrete tokenizer
and model remain in `PhoBertSentenceEncoder`; token IDs and masks remain transient.

## Request data flow

For one HTTP request:

1. Validate and trim `text`; validate `top_k`.
2. Call existing `split_article_text(text)`. This reuses normalization and punctuation-aware
   splitting into parts of at most 200 normalized whitespace words.
3. Assign request-local part numbers in source order and call the shared VnCoreNLP segmentation
   service.
4. Assign a stable zero-based query-sentence index in the returned order.
5. Encode all query sentences with the shared validated PhoBERT sentence encoder.
6. For each query vector, ask the PostgreSQL search repository for the exact best matching sentence
   in each eligible article and retain that query's best `top_k` articles.
7. Merge candidates from all query sentences, retaining the maximum-scoring pair per article.
8. Sort the resulting distinct articles deterministically and return the first `top_k`.

The union of each query sentence's exact top `top_k` distinct articles is sufficient for the final
exact top `top_k`: an article outside that per-query top set cannot outrank the `top_k` articles
that already score higher for the query sentence on which its own maximum is achieved.

## Exact cosine retrieval

The PostgreSQL repository joins:

- `sentence_embeddings` for the stored vector and `model_name`;
- `segmented_sentences` for article and sentence metadata;
- `crawl_urls` for URL and current crawl status;
- the first ordered `processed_paragraphs` title part for the optional display title.

For each query vector, the repository computes pgvector cosine distance, chooses the lowest-distance
sentence per `crawl_url_id`, orders those distinct articles, and limits them to `top_k`. It filters
to:

- `sentence_embeddings.model_name == settings.phobert_model_name`;
- `crawl_urls.status == "completed"`;
- non-null cosine distances.

Application ranking uses the unrounded value:

```text
cosine_score = 1 - cosine_distance
article_score = max(cosine_score(query_sentence, article_sentence))
```

When two pairs give the same maximum score for one article, matched-pair selection uses
query-sentence index ascending and then matched segmented-sentence ID ascending. Final article
ordering uses article score descending and then `crawl_url_id` ascending.

Only serialization and logging round the score to six decimal places.

## HTTP contract

### Request

```http
POST /api/v1/search/articles
Content-Type: application/json
```

```json
{
  "text": "Đoạn văn cần tìm kiếm...",
  "top_k": 10
}
```

- `text` is required, must be nonblank after trimming, and is limited to 10,000 Unicode characters.
- `top_k` defaults to `10` and must be between `1` and `50`, inclusive.

### Successful response

```json
{
  "status": "success",
  "top_k": 10,
  "returned_count": 1,
  "query": {
    "segment_count": 2,
    "segmented_sentences": [
      "Giá_vé máy_bay đi Singapore giảm_mạnh .",
      "Nhiều hãng_hàng_không mở thêm chuyến ."
    ]
  },
  "articles": [
    {
      "rank": 1,
      "crawl_url_id": 261,
      "title": "Giá vé máy bay quốc tế giảm",
      "url": "https://vnexpress.net/example.html",
      "score": 0.873421,
      "matched_query_sentence": "Giá_vé máy_bay đi Singapore giảm_mạnh .",
      "matched_article_sentence": {
        "id": 9842,
        "text": "Giá_vé đến Singapore đang giảm_mạnh .",
        "paragraph_num": 4,
        "paragraph_part_num": 1,
        "segment_num": 1
      }
    }
  ]
}
```

`title` is the first title part in paragraph/part order and may be `null`. The response always uses
HTTP 200 when search completes, including an empty eligible corpus; the empty-corpus response has
`returned_count: 0` and `articles: []`.

## Model lifecycle and concurrency

Search dependencies are composed lazily on the first search request and cached for later requests.
The application startup lifespan must not load VnCoreNLP, transformers, or torch, so a missing model
does not prevent health or crawler startup.

The cached search use case owns a process-local lock around VnCoreNLP segmentation and PhoBERT
inference. This serializes access to model instances whose thread-safety and peak-memory behavior
are not guaranteed. The lock is released before the PostgreSQL similarity query so database work
does not unnecessarily block later inference.

The first search request may therefore be slower because it loads the models. A process with
multiple Uvicorn workers has one model copy and one lock per worker; v1 does not add cross-process
coordination.

## Error handling

Search-specific errors are translated only in the search route. No global exception handler is
introduced, so existing HTTP contracts remain unchanged.

- HTTP 422: request-schema violations, blank normalized content, or a preprocessing rejection caused
  by the supplied text.
- HTTP 503: VnCoreNLP/PhoBERT load or inference failure, invalid model output such as no usable
  segmented sentence or an all-zero query vector, or PostgreSQL search unavailability.
- HTTP 500: unexpected programming/runtime errors handled by FastAPI's existing default behavior.
- HTTP 200 with an empty article list: no eligible vectors for the configured model, or an empty
  eligible corpus.

Client-visible 503 messages use a stable generic detail and do not expose model paths, database
URLs, SQL, or stack traces. Detailed causes remain in server logs.

## Terminal logging

The feature uses the standard Python logger so output appears with Uvicorn logs. A successful
request emits one summary and one row per returned article:

```text
SEARCH status=success query_segments=2 requested_top_k=10 returned=10 duration_ms=842
SEARCH_RESULT rank=1 crawl_url_id=261 score=0.873421 sentence_id=9842 url="https://vnexpress.net/example.html"
```

Each `SEARCH_RESULT` includes a single-line matched-sentence preview: replace line breaks with spaces
and truncate to 160 Unicode characters. Logs must not contain full vectors, token IDs, attention
masks, database credentials, or stack traces in success records. Expected failures emit
`SEARCH status=failed category=<category>` with a safe reason; unexpected exceptions continue
through the existing Uvicorn error logger.

## Configuration and documentation

The endpoint reuses the existing settings:

- `APP_DATABASE_URL`
- `APP_SEGMENTER_MODEL_DIR`
- `APP_PHOBERT_MODEL_NAME`
- `APP_PHOBERT_MODEL_DIR`
- `APP_EMBEDDING_BATCH_SIZE`
- `APP_EMBEDDING_MAX_LENGTH`

No new setting is required. README documentation will add the request/response contract, a curl
example, the lazy first-request cost, and the requirement that corpus embeddings use the configured
model. `.env.example` will list the existing model and embedding settings shown above; their defaults
and runtime meaning must not change.

## Verification strategy

The repository explicitly forbids adding automated tests for this task. Verification therefore
uses static checks and targeted manual evidence:

1. Run `make format` before committing implementation changes.
2. Run `make verify`; if unrelated baseline notebooks fail, report them precisely and also run
   backend-source Ruff format/check, mypy, and all UI checks separately.
3. Start the real FastAPI application with the configured PostgreSQL, cached VnCoreNLP, and cached
   PhoBERT model.
4. Call search with a one-sentence input and a multi-sentence paragraph.
5. Verify `crawl_url_id` uniqueness, descending raw scores, stable tie ordering, and
   `returned_count <= top_k`.
6. Independently query pgvector cosine distance for the returned top pair and compare the score.
7. Repeat an identical request and compare ordered response IDs and scores.
8. Exercise blank, oversized, and invalid-`top_k` requests and confirm HTTP 422.
9. Record relevant row counts before and after search to prove the endpoint performs no writes.
10. Smoke-check `GET /api/v1/health` and application startup without eagerly constructing search
    models.
11. Exercise the refactored shared segmentation and encoding paths through both the search request
    and focused CLI/manual checks without resetting or destructively recreating the database.

The baseline worktree currently has a repository-wide `make verify` formatting failure in
`backend/notebook/analysisData/analyze_txt_corpus.ipynb`. That pre-existing notebook is outside this
feature's scope and must not be reformatted incidentally.

## Compatibility guarantees

- No existing route, response schema, Make target, database column, constraint, or stored data is
  removed or renamed.
- The query path performs no persistence.
- Existing preprocessing and embedding behavior is moved only as necessary to share exact logic;
  batch summaries, failure isolation, metadata propagation, and transactional writes remain intact.
- The `codex/embedding-cosine-index` worktree/branch is not modified or required by exact v1.
- Implementation occurs on the isolated `codex/semantic-article-search-api` branch.
