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

Pipeline xử lý văn bản gồm ba bước độc lập. Đầu tiên, normalize toàn bộ bài đã crawl thành công
hoặc một bài cụ thể; bước này không import, load hay yêu cầu VnCoreNLP:

```bash
make preprocess
make preprocess CRAWL_ID=261
```

Tiếp theo, tải model VnCoreNLP một lần. Command kiểm tra cache trước nên nếu đã có
`VnCoreNLP-1.2.jar` và `models/wordsegmenter`, nó chỉ in `MODEL cached` và không gọi mạng:

```bash
make download-segmenter-model
```

Cuối cùng, segment các row đã normalize và lưu mỗi sentence thành một row riêng:

```bash
make segment
make segment CRAWL_ID=261
```

Trong bước normalize, các dấu `-`, `–`, `—` đều được thay bằng khoảng trắng trước khi gom
whitespace. Nếu một block vượt 200 normalized whitespace words, preprocessing tự tách block đó:
ưu tiên dấu `.`, `?`, `!`, `:` gần giới hạn nhất và giữ dấu câu ở part phía trước; nếu một clause
vẫn quá dài thì cắt theo ranh giới word.

Command chỉ đọc các row `crawl_urls` có `status='completed'` và `file_path` khác null. Path
`data/...` hoặc `backend/data/...` đều được resolve bên trong thư mục `backend/`; path thoát ra
ngoài thư mục này bị từ chối.

Mỗi block `<s>` được bỏ thẻ nhưng giữ `docid`, `num`, `wdcount`, `type` và thứ tự nguồn. Text
được chuẩn hóa ký tự typography, xóa zero-width/BOM, đổi NBSP thành space, gom space/tab và
loại literal `&gt;`. Mỗi processed part giữ `paragraph_num` gốc và dùng
`paragraph_part_num` bắt đầu từ 1; `source_word_count`, `source_text` và `normalized_text` được
tính riêng cho part. Bảng `segmented_sentences` liên kết từng segment với parent part và sao chép
metadata cần thiết.

Preprocess log `PREPROCESS_SPLIT` bằng metadata, original word count và số part nhưng không in nội
dung nguồn. Segmentation vẫn từ chối toàn bộ document nếu bất kỳ `normalized_text` nào vượt 200
words, như một guard chống dữ liệu cũ hoặc lỗi splitter. Document lỗi giữ nguyên snapshot segment
trước đó và batch tiếp tục với document kế tiếp. Chạy lại một document hợp lệ sẽ thay thế toàn bộ
segment trong một transaction. Model download cần network, nhưng preprocessing và segmentation
thông thường không tự tải model.

Schema dùng `paragraph_part_num`; database cũ phải được recreate trước khi chạy pipeline vì
`create_all()` không tự thêm cột hoặc thay unique constraint.

## Semantic article search

Trước khi tìm kiếm, corpus phải có sentence embedding PhoBERT tương ứng. Tạo embedding cho toàn
bộ corpus hoặc một bài cụ thể bằng:

```bash
make embed
make embed CRAWL_ID=<id>
```

Endpoint `POST /api/v1/search/articles` nhận JSON gồm `text` và `top_k`. `text` là chuỗi bắt buộc,
không được rỗng sau khi trim và dài tối đa 10.000 ký tự. `top_k` là số nguyên strict từ 1 đến 50,
mặc định là 10.

```bash
curl -sS -X POST http://localhost:8000/api/v1/search/articles \
  -H 'Content-Type: application/json' \
  -d '{"text":"Giá vé máy bay đi Singapore giảm mạnh.","top_k":10}'
```

Response thành công có `status`, `top_k`, `returned_count`, thông tin query sau segmentation và
danh sách `articles`. Mỗi article gồm `rank`, `crawl_url_id`, `title`, `url`, `score`, câu query
khớp nhất và câu trong article khớp nhất kèm metadata paragraph/segment. Mỗi `crawl_url_id` chỉ
xuất hiện một lần. `score` là cosine similarity lớn nhất trong mọi cặp câu query-câu article,
không phải trung bình; kết quả được sắp ổn định theo score giảm dần rồi `crawl_url_id` tăng dần.

Request sai giới hạn hoặc không còn nội dung sau preprocessing trả HTTP 422. Lỗi model, cache
hoặc dịch vụ tìm kiếm trả HTTP 503 với thông báo chung. Corpus không có article đủ điều kiện trả
HTTP 200 với `articles` rỗng và `returned_count` bằng 0.

VnCoreNLP và PhoBERT được load lazy ở request tìm kiếm đầu tiên; mỗi process Uvicorn giữ một bản
model trong bộ nhớ. Query đã normalize, câu segmented, token, mask và vector chỉ tồn tại tạm thời;
API search không ghi query hay kết quả vào database và các câu query sau xử lý được trả trực tiếp
trong response.

Terminal ghi một dòng `SEARCH` tóm tắt cho mỗi request thành công/thất bại và một dòng
`SEARCH_RESULT` cho mỗi article trả về. Log không chứa query đầy đủ, token, mask, vector, database
URL, model path hoặc credential trong URL.

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
