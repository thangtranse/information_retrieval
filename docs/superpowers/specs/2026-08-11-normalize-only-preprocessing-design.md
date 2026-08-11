# Normalize-only preprocessing design

## Goal

Mở rộng CLI preprocessing để người vận hành có thể chỉ tạo `normalized_text` từ
`source_text` mà không load hoặc gọi VnCoreNLP. Đồng thời, mọi dấu gạch ngang `-`, `–`, `—`
được thay bằng khoảng trắng trong quá trình normalize.

## Scope

In scope:

- Thêm argument `--normalize-only` cho
  `python -m information_retrieval.presentation.cli.preprocess`.
- Cho phép kết hợp `--normalize-only` với `--crawl-id=<id>`.
- Không cho phép kết hợp `--normalize-only` với `--download-model-only`.
- Trong normalize-only mode, không kiểm tra model cache, không load Java/VnCoreNLP và không gọi
  `WordSegmenter.segment`.
- Lưu `segmented_sentences` dưới dạng JSONB empty array `[]`.
- Đổi `-`, `–`, `—` thành một khoảng trắng trước bước collapse space/tab.
- Giữ nguyên hành vi mặc định của `make preprocess`: normalize rồi word segmentation.
- Cập nhật README và manual smoke checks.

Out of scope:

- Thêm automated tests.
- Thay đổi database schema hoặc migration.
- Thêm API endpoint hoặc UI.
- Tách normalization và segmentation thành hai bảng hay hai pipeline độc lập.

## CLI contract

Các command hợp lệ:

```bash
make preprocess
make preprocess ARGS=--crawl-id=261
make preprocess ARGS=--normalize-only
make preprocess ARGS="--normalize-only --crawl-id=261"
make download-segmenter-model
```

Command không hợp lệ:

```bash
cd backend
uv run python -m information_retrieval.presentation.cli.preprocess \
  --download-model-only --normalize-only
```

Argparse phải trả exit code khác `0` và giải thích hai mode này không thể kết hợp.

## Application design

Domain khai báo `PreprocessingMode` gồm đúng hai giá trị:

- `normalize_and_segment`: hành vi mặc định hiện tại.
- `normalize_only`: chỉ normalize và lưu `segmented_sentences=[]`.

`PreprocessCrawledArticles.execute` nhận mode cùng optional `crawl_id`. Segmenter trở thành optional
dependency: bắt buộc khi mode là `normalize_and_segment`, không được gọi khi mode là
`normalize_only`. Nếu full mode không có segmenter, use case raise `ArticlePreprocessingError`
thay vì silently lưu empty segmentation.

CLI parse `--normalize-only` thành application mode. Import adapter `VnCoreNlpWordSegmenter` phải
được lazy-load bên trong download/full-mode branch; normalize-only không được import
`py_vncorenlp`, resolve model directory hoặc khởi tạo segmenter. Do đó normalize-only chạy được
trên máy chưa tải model và chưa cài Java.

## Normalization contract

`CHAR_MAP` map cả ba dash characters sang space:

```python
CHAR_MAP = {
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "-": " ",
    "–": " ",
    "—": " ",
}
```

Sau CHAR_MAP, normalization tiếp tục xóa zero-width space, BOM, đổi NBSP thành space, collapse
`[ \t]+` và strip. Ví dụ bắt buộc:

| Input | Output |
|---|---|
| `A-B` | `A B` |
| `A – B` | `A B` |
| `2027—2028` | `2027 2028` |

## Persistence and rerun behavior

Không thay đổi schema `processed_paragraphs`; JSONB hiện tại chấp nhận empty array. Repository vẫn
thay thế toàn bộ snapshot của một document trong một transaction.

- Chạy normalize-only sau full mode sẽ cố ý thay các segmentation cũ bằng `[]`.
- Chạy full mode sau normalize-only sẽ tạo lại non-empty `segmented_sentences`.
- Failure trước transaction không xóa snapshot thành công trước đó.

## Output and error behavior

Summary hiện tại được giữ nguyên:

```text
SUMMARY selected=<n> processed=<n> paragraphs=<n> failed=<n>
```

Normalize-only không in log load VnCoreNLP. File lỗi, metadata lỗi hoặc normalized text rỗng vẫn
được ghi nhận theo từng document như hiện tại. Database errors vẫn rollback và dừng command.

## Verification

Repository không có automated tests theo `AGENTS.md`. Verification gồm:

- `ruff format --check src`, `ruff check src`, `mypy src`.
- UI format/lint/typecheck/build hiện có để phát hiện ảnh hưởng ngoài ý muốn.
- Inline normalization smoke cho đủ `-`, `–`, `—`.
- Normalize-only end-to-end cho một completed crawl row, xác nhận JSONB bằng `[]` và output không có
  VnCoreNLP load log.
- Full-mode end-to-end cùng row, xác nhận JSONB trở lại non-empty.
- Argparse smoke xác nhận hai download/normalize-only flags bị từ chối khi kết hợp.

Full `make verify` vẫn có baseline failure do các notebook PhoBERT cũ chưa đúng Ruff format; không
format hoặc sửa các notebook đó trong phạm vi này.
