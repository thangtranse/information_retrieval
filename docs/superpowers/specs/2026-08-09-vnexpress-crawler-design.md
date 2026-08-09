# VnExpress Sequential Crawler Design

## Goal

Xây dựng crawler backend chạy tuần tự để khám phá URL bài viết từ các trang danh mục VnExpress, chống lưu trùng bằng canonical URL, tải nội dung bài viết thành file UTF-8 dạng các block `<s>`, và quản lý trạng thái xử lý trong PostgreSQL hỗ trợ pgvector. Cùng một use case tải bài viết được dùng bởi batch script và API crawl thủ công.

## Scope

### In scope

- Cấu hình base domain và danh sách seed URL qua environment.
- Khám phá liên kết bài viết từ các seed page bằng anchor contract của VnExpress.
- Canonicalize URL bằng cách loại bỏ query parameters và fragment.
- Lưu URL duy nhất và trạng thái xử lý trong một bảng PostgreSQL.
- Xử lý tuần tự các URL mới trong cùng một lần chạy script.
- Tải lại một URL theo yêu cầu qua FastAPI, kể cả khi bài đã hoàn tất trước đó.
- Trích title, description và paragraph từ article contract đã xác định.
- Ghi file UTF-8 dưới `backend/data/articles/`.
- Chạy UI, backend và PostgreSQL/pgvector bằng Docker Compose.

### Out of scope

- Concurrent hoặc asynchronous crawling.
- Automatic retry, retry queue, scheduler hoặc background worker.
- Embedding generation, vector columns và semantic search.
- Crawler UI.
- Crawl website hoặc HTML structure khác VnExpress.
- Lưu lịch sử các lần crawl hay version nội dung.
- Automated tests, theo quy định của repository.

## Architecture

Giải pháp sử dụng synchronous `httpx` và BeautifulSoup. Batch script gọi hai application use case theo thứ tự: khám phá URL từ seed pages, sau đó tải từng URL mới. FastAPI gọi lại use case tải bài viết cho một URL do người dùng cung cấp.

Backend tiếp tục giữ dependency hướng vào trong:

- `domain` định nghĩa crawl entity, status và invariant độc lập framework.
- `application` sở hữu use case và các port cho HTTP source, repository và file storage.
- `infrastructure` triển khai HTTP client/parser, PostgreSQL repository và UTF-8 file writer.
- `presentation` cung cấp FastAPI route, request/response schema và CLI entrypoint.
- Composition root kết nối các concrete adapter với use case.

Không thêm database abstraction ngoài các port hiện đang cần. PostgreSQL extension `vector` được bật để stack hỗ trợ pgvector, nhưng feature này chưa tạo embedding hoặc vector column.

## Configuration Contract

`backend/.env.example` mở rộng contract hiện tại:

```dotenv
APP_NAME=Information Retrieval API
APP_ENVIRONMENT=development
APP_UI_ORIGIN=http://localhost:5173

APP_DATABASE_URL=postgresql+psycopg://information_retrieval:information_retrieval@postgres:5432/information_retrieval
APP_CRAWLER_BASE_DOMAIN=https://vnexpress.net/
APP_CRAWLER_SEED_URLS=["https://vnexpress.net/kinh-doanh"]
```

`APP_CRAWLER_SEED_URLS` là JSON array để Pydantic Settings parse thành danh sách chuỗi mà không phụ thuộc delimiter tự đặt. System environment tiếp tục được ưu tiên hơn file `.env`.

## URL Policy

### Canonicalization

Mọi URL đi qua một canonicalization boundary duy nhất trước khi validate, lookup hoặc insert:

1. Resolve URL tương đối dựa trên URL trang chứa anchor.
2. Chỉ cho phép scheme `http` hoặc `https`.
3. So sánh hostname đã normalize với hostname của `APP_CRAWLER_BASE_DOMAIN`.
4. Loại bỏ toàn bộ query string và fragment.
5. Chuẩn hóa phần URL còn lại thành absolute URL.
6. Với URL bài viết, path phải kết thúc chính xác bằng `.html` sau canonicalization.

Ví dụ:

```text
https://vnexpress.net/example.html?utm_source=homepage#box_comment
```

được lưu thành:

```text
https://vnexpress.net/example.html
```

Unique constraint trên canonical URL là lớp bảo vệ cuối cùng chống bản ghi trùng. Redirect chỉ được chấp nhận khi URL cuối cùng vẫn thuộc configured hostname; quy tắc này ngăn API trở thành một SSRF proxy tới host tùy ý.

### Discovery anchor contract

Một anchor chỉ được xem là ứng viên bài viết khi thỏa tất cả điều kiện:

- Có attribute `href` không rỗng.
- Có attribute `data-itm-source`.
- Có attribute `title` không rỗng.
- Visible text sau normalize whitespace không rỗng.
- Sau case-fold và normalize whitespace, `title` bằng visible text hoặc một giá trị chứa giá trị còn lại.
- Canonical URL thuộc configured hostname và kết thúc bằng `.html`.

Các anchor không hợp lệ bị bỏ qua và không tạo database row.

## Database Model

Database có đúng một bảng nghiệp vụ `crawl_urls`:

| Column | Type | Constraint and meaning |
|---|---|---|
| `id` | `BIGINT` | Primary key; dùng làm `docid` trong file |
| `url` | `TEXT` | Canonical URL, unique, not null |
| `status` | `VARCHAR` | Chỉ nhận `pending`, `completed`, `failed` |
| `file_path` | `TEXT` | Nullable, đường dẫn tương đối từ `backend/` |
| `error_reason` | `TEXT` | Nullable, nguyên nhân thất bại gần nhất |
| `created_at` | timezone-aware timestamp | Thời điểm tạo bản ghi |
| `updated_at` | timezone-aware timestamp | Thời điểm xử lý gần nhất |

Table creation là idempotent khi backend hoặc script khởi động. PostgreSQL init script bật extension `vector`. Không thêm Alembic ở phạm vi một bảng; thay đổi schema tương lai phải đánh giá lại nhu cầu migration tool.

## Article Extraction Contract

URL nội dung chỉ hợp lệ khi canonical path kết thúc bằng `.html`. Parser yêu cầu đúng container:

```css
article#fck_detail_gallery.fck_detail
```

Bên trong article, parser duyệt DOM order và tạo block từ:

- `h1` thành `type="title"`.
- `p.description` thành `type="description"`.
- `p.Normal` thành `type="paragraph"`.

Text được lấy từ toàn bộ descendant text, decode HTML entities và normalize mọi whitespace sequence thành một space. Block rỗng sau normalize bị loại bỏ. Không giữ HTML con trong nội dung block.

Thiếu article container, không có title, hoặc không có bất kỳ content block hợp lệ nào là parse failure có nguyên nhân cụ thể. Multiple paragraph blocks được giữ nguyên thứ tự.

## Text File Contract

Mỗi database row dùng một path ổn định:

```text
backend/data/articles/<id>.txt
```

Mỗi block nằm trên một dòng và có dạng:

```xml
<s docid="42" num="1" wdcount="6" type="title">Giá vàng tăng mạnh trong ngày</s>
<s docid="42" num="2" wdcount="11" type="description">Thị trường vàng trong nước tiếp tục có nhiều biến động.</s>
<s docid="42" num="3" wdcount="14" type="paragraph">Giá vàng miếng được các doanh nghiệp điều chỉnh tăng vào đầu giờ sáng.</s>
```

Các invariant:

- File encoding là UTF-8.
- `docid` bằng `crawl_urls.id`.
- `num` bắt đầu từ `1` và tăng liên tục theo thứ tự block trong article.
- `wdcount` là số token phân tách bởi whitespace sau khi text đã normalize.
- `type` chỉ nhận `title`, `description`, `paragraph`.
- Text được escape tối thiểu cho `&`, `<` và `>` để không phá cấu trúc thẻ.
- Writer ghi file tạm trong cùng thư mục rồi atomic replace file đích; database chỉ chuyển sang `completed` sau khi replace thành công.

## Batch Script Flow

CLI chạy từ `backend/`:

```bash
uv run python -m information_retrieval.presentation.cli.crawl
```

Luồng xử lý:

1. Load và validate settings.
2. Khởi tạo database schema idempotently.
3. Với từng seed URL theo đúng thứ tự cấu hình:
   - Validate URL thuộc base hostname.
   - Fetch HTML đồng bộ.
   - Extract và canonicalize eligible article URLs.
   - Insert URL chưa tồn tại với status `pending`; giữ nguyên bản ghi đã tồn tại.
4. Giữ danh sách ID vừa insert trong lần chạy hiện tại.
5. Với từng ID mới theo thứ tự khám phá:
   - Fetch và validate final redirected URL.
   - Parse article blocks.
   - Serialize và atomic write file.
   - Update row thành `completed`, lưu relative `file_path`, clear `error_reason`, update `updated_at`.
   - Nếu bất kỳ bước nào lỗi, update ngay row thành `failed`, lưu nguyên nhân, update `updated_at`, không retry và tiếp tục ID kế tiếp.
6. In summary gồm seed count, discovered count, inserted count, completed count và failed count.

Script không tải lại các URL đã tồn tại trước khi lượt chạy bắt đầu. Quy tắc này tránh việc mỗi lần chạy seed lại tải toàn bộ kho bài cũ.

CLI trả exit code `0` khi mọi seed và article vừa phát hiện đều xử lý thành công, kể cả trường hợp không có URL mới. CLI trả exit code `1` nếu có ít nhất một seed fetch failure hoặc article failure; các lỗi còn lại vẫn được xử lý và in summary trước khi tiến trình kết thúc.

Log format cung cấp tiến trình trực tiếp:

```text
DISCOVER seed=https://vnexpress.net/kinh-doanh found=20 inserted=12 existing=8
CRAWL id=42 status=completed path=data/articles/42.txt
CRAWL id=43 status=failed reason="article#fck_detail_gallery.fck_detail not found"
SUMMARY seeds=1 discovered=20 inserted=12 completed=11 failed=1
```

## Manual Crawl API

Endpoint:

```http
POST /api/v1/crawler/articles
Content-Type: application/json

{
  "url": "https://vnexpress.net/example.html?utm_source=test"
}
```

Behavior:

1. Canonicalize và validate URL trước khi fetch.
2. Invalid scheme, hostname hoặc `.html` suffix bị từ chối và không insert row.
3. Nếu canonical URL chưa tồn tại, insert `pending`; nếu đã tồn tại, reuse row hiện có.
4. Luôn fetch lại bài, kể cả row đang `completed`.
5. Khi thành công, atomic replace file cùng `<id>.txt`, update `status`, `file_path`, `error_reason` và `updated_at`.
6. Khi thất bại, update `failed`, lưu nguyên nhân và `updated_at`; không retry.
7. Nếu row đã có file từ lần thành công trước nhưng lần tải lại thất bại, giữ file cùng `file_path` cũ để không xóa dữ liệu hợp lệ; status `failed` và `error_reason` phản ánh lần xử lý gần nhất.

Success response:

```json
{
  "id": 42,
  "url": "https://vnexpress.net/example.html",
  "status": "completed",
  "file_path": "data/articles/42.txt",
  "error_reason": null,
  "updated_at": "2026-08-09T10:30:00+07:00"
}
```

Invalid scheme, hostname hoặc suffix trả `422 Unprocessable Entity` và không tạo row. Upstream network/HTTP failure trả `502 Bad Gateway`; article structure không đúng contract trả `422 Unprocessable Entity`. Hai loại failure sau chỉ trả response sau khi row đã được cập nhật thành `failed`, và response có `id`, canonical `url`, `status="failed"`, `error_reason`. Database hoặc file-system failure trả `500 Internal Server Error` mà không tuyên bố bài đã hoàn tất.

## Docker Topology

Root `compose.yaml` có ba service:

- `postgres`: PostgreSQL image có pgvector, named volume, healthcheck và init SQL bật extension `vector`.
- `backend`: Python 3.14 image, cài dependency bằng `uv`, chạy FastAPI app, phụ thuộc PostgreSQL healthy và bind mount `./backend/data:/app/data`.
- `ui`: Node build/runtime cho React website, expose website và cấu hình backend URL phù hợp với browser.

Backend Docker image cũng có thể chạy CLI bằng cách override service command. `backend/data/articles/` được ignore khỏi Git nhưng thư mục được giữ bằng placeholder phù hợp để mount path luôn rõ ràng.

## Error Handling

- Seed fetch failure được log cùng seed URL; script tiếp tục seed kế tiếp và thể hiện lỗi trong summary/exit result.
- Invalid discovery anchors bị bỏ qua, không tạo failed row vì chúng chưa phải accepted article URL.
- Accepted article URL gặp network, redirect-policy, HTTP status, parse hoặc write failure được chuyển ngay sang `failed` với nguyên nhân ngắn gọn, không chứa response body hay secret.
- Không có automatic retry trong CLI hoặc API.
- Một article failure không chặn article kế tiếp trong batch.
- File chỉ được replace sau khi serialize hoàn chỉnh; partial file không trở thành artifact chính thức.

## Verification Strategy

Repository chủ động không có automated test suite. Implementation được kiểm tra bằng static verification và smoke checks có kiểm soát:

```bash
make format
make verify
docker compose config
docker compose build
docker compose up -d postgres backend ui
docker compose ps
```

Smoke checks phải xác nhận:

- Health API phản hồi khi chạy trong Compose.
- PostgreSQL có extension `vector`.
- `crawl_urls` được tạo với unique URL và status constraint.
- Invalid manual URL có query bị canonicalize trước validation, còn wrong host và non-`.html` URL bị từ chối mà không tạo row.
- Một controlled HTML fixture dùng trong manual smoke command tạo đúng block order, `wdcount`, escaping và UTF-8 file; fixture này là dữ liệu xác minh thủ công, không tạo automated test suite.
- API crawl lại cùng canonical URL reuse cùng ID, replace cùng file và chỉ cập nhật row hiện tại.

Live crawl tới VnExpress chỉ chạy khi người thực thi cho phép network access. Lint, type checking, build và local controlled smoke checks không được mô tả như bằng chứng end-to-end với website thật.

## File Responsibility Map

Implementation plan sẽ khóa exact paths dựa trên các trách nhiệm sau:

- Domain files: crawl URL entity/status và extracted content block.
- Application files: discovery use case, article crawl use case và boundary protocols.
- Infrastructure files: settings, synchronous HTTP client, VnExpress discovery/parser, SQLAlchemy model/repository, schema initialization và atomic text writer.
- Presentation files: FastAPI crawl route/schema/dependencies và CLI module.
- Deployment files: backend/UI Dockerfiles, Compose file và PostgreSQL extension init script.
- Documentation/config files: `.env.example`, README, Makefile, Git ignore và dependency manifests.

Không thay đổi UI feature code ngoài cấu hình/build cần thiết để chạy website trong Compose.
