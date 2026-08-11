# Information Retrieval

Monorepo gồm FastAPI backend chạy Python 3.14 và React website. Hai phần giữ dependency và source code riêng; root chỉ điều phối workflow.

## Prerequisites

- `uv`
- Node.js LTS và npm
- Java và `wget` cho VnCoreNLP (`brew install wget openjdk` trên macOS)

## Setup

```bash
make setup
cp backend/.env.example backend/.env
cp ui/.env.example ui/.env
```

Hai file `.env` chỉ dùng local và không được commit; thay đổi giá trị `APP_*` trong `backend/.env` khi cần cấu hình backend development.

## Run locally

Terminal 1:

```bash
make dev-backend
```

Terminal 2:

```bash
make dev-ui
```

Mở `http://localhost:5173`. API docs ở `http://localhost:8000/docs`; health endpoint ở `http://localhost:8000/api/v1/health`.

Crawler cần PostgreSQL. Chạy toàn bộ stack bằng Docker Compose:

```bash
docker compose up -d postgres backend ui
```

## Crawler

Batch script khám phá URL từ seed pages rồi tải tuần tự các bài mới trong cùng lần chạy:

```bash
make crawl
```

Mặc định command không tải lại các URL đã có trong database. Để lấy toàn bộ record đang có
`status='failed'` và thử tải lại tuần tự sau pha discovery, truyền flag qua biến `ARGS`:

```bash
make crawl ARGS=--retry-failed
```

Retry thành công chuyển record sang `completed`, ghi lại file và cập nhật `updated_at`. Nếu vẫn
lỗi, record giữ trạng thái `failed` với `error_reason` và `updated_at` mới nhất. Flag không xử lý
các record `completed`, và một URL mới thất bại trong chính lượt chạy hiện tại không bị retry ngay.

Tải lại một bài cụ thể qua API (luôn fetch lại, kể cả bài đã hoàn tất):

```bash
curl -X POST http://localhost:8000/api/v1/crawler/articles \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://vnexpress.net/example.html"}'
```

File nội dung ghi UTF-8 dạng block `<s>` dưới `backend/data/articles/<id>.txt`; trạng thái xử lý lưu ở bảng `crawl_urls`. Cấu hình `APP_DATABASE_URL`, `APP_CRAWLER_BASE_DOMAIN` và `APP_CRAWLER_SEED_URLS` (JSON array) trong `backend/.env`.

## Text preprocessing

Tải model VnCoreNLP một lần. Command kiểm tra cache trước nên nếu đã có
`VnCoreNLP-1.2.jar` và `models/wordsegmenter`, nó chỉ in `MODEL cached` và không gọi mạng:

```bash
make download-segmenter-model
```

Tiền xử lý tuần tự toàn bộ bài đã crawl thành công hoặc một bài cụ thể:

```bash
make preprocess
make preprocess ARGS=--crawl-id=261
```

Command chỉ đọc các row `crawl_urls` có `status='completed'` và `file_path` khác null. Path
`data/...` hoặc `backend/data/...` đều được resolve bên trong thư mục `backend/`; path thoát ra
ngoài thư mục này bị từ chối.

Mỗi block `<s>` được bỏ thẻ nhưng giữ `docid`, `num`, `wdcount`, `type` và thứ tự nguồn. Text
được chuẩn hóa ký tự typography, xóa zero-width/BOM, đổi NBSP thành space, gom space/tab và
loại literal `&gt;` trước khi VnCoreNLP word segmentation. Bảng `processed_paragraphs` liên kết
với `crawl_urls.id` bằng `crawl_url_id` và lưu danh sách `segmented_sentences` dưới dạng JSONB.
Chạy lại một document sẽ thay thế toàn bộ paragraph của document đó trong một transaction;
model download cần network nhưng preprocessing bình thường không cần network.

## Architecture

- `backend/domain`: model và invariant thuần Python.
- `backend/application`: use case và port do application sở hữu.
- `backend/infrastructure`: config và adapter triển khai port.
- `backend/presentation`: HTTP route, schema và dependency wiring.
- `ui/src/features`: code thuộc từng feature.
- `ui/src/shared`: primitive thật sự dùng chung giữa nhiều feature.

Dependency backend đi từ lớp ngoài vào lớp trong. UI component không gọi `fetch` trực tiếp mà đi qua feature API và shared HTTP boundary.

## Verification

```bash
make verify
```

Project chủ động không có automated tests theo quy ước trong `AGENTS.md`; verification gồm lint, type-check, production build và manual smoke check.
