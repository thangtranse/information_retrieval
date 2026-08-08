# Backend `.env` Configuration Design

## Goal

Cho phép backend tự động đọc cấu hình local từ `backend/.env`, đồng thời cung cấp file mẫu an toàn để mọi lập trình viên có cùng contract cấu hình mà không commit secret.

## Configuration Contract

`backend/.env.example` được commit với ba biến:

```dotenv
APP_NAME=Information Retrieval API
APP_ENVIRONMENT=development
APP_UI_ORIGIN=http://localhost:5173
```

`backend/.env` được tạo local bằng cách copy file mẫu và không được Git theo dõi. Quy tắc `.gitignore` hiện tại đã bỏ qua mọi file `.env` nhưng cho phép commit `.env.example`.

## Runtime Behavior

`Settings` tiếp tục dùng prefix `APP_`, immutable configuration và cache một instance. `SettingsConfigDict` được mở rộng với `env_file=".env"` và `env_file_encoding="utf-8"`.

Backend commands chạy từ thư mục `backend/`, vì vậy `.env` được phân giải thành `backend/.env`. Biến môi trường hệ thống có độ ưu tiên cao hơn giá trị trong file `.env`, theo hành vi chuẩn của Pydantic Settings.

## Files

- Create `backend/.env.example`: contract cấu hình được commit.
- Create local ignored `backend/.env`: cấu hình development mặc định.
- Modify `backend/src/information_retrieval/infrastructure/config.py`: tự đọc `.env`.
- Modify `README.md`: hướng dẫn copy cả backend và UI environment files.

## Constraints

- Không commit secret hoặc `backend/.env`.
- Không thêm dependency; `pydantic-settings` hiện có đảm nhận việc đọc dotenv.
- Không thêm automated tests theo `AGENTS.md`.
- Giữ Python 3.14 và workflow `uv` hiện tại.
- Docstring/comment chỉ giải thích WHY, không mô tả WHAT.

## Verification

- Ruff kiểm tra style backend.
- mypy strict kiểm tra type safety.
- Smoke command xóa cache settings, đọc `backend/.env`, và xác nhận ba giá trị được parse đúng.
- `git check-ignore backend/.env` xác nhận file local không thể bị commit ngoài ý muốn.
- `git status` xác nhận chỉ `.env.example`, source config, README và spec/plan được theo dõi.

## Out of Scope

- Production secrets management.
- Environment-specific files như `.env.prod` hoặc `.env.staging`.
- Database, authentication và Information Retrieval business configuration.
