# Phát triển local (từ source)

Dùng khi bạn **sửa code** `api/` hoặc `web/` và muốn hot-reload, không rebuild Docker image mỗi lần.

## Yêu cầu thêm

| Công cụ | Ghi chú |
| --- | --- |
| [uv](https://docs.astral.sh/uv/) | Python package manager cho API |
| [pnpm](https://pnpm.io/) | JavaScript (workspace root) |
| Node.js | Theo `.nvmrc` ở root repo |
| Docker | Chỉ chạy **middleware** (DB, Redis, vector DB) |

Trên Windows: chạy script `./dev/*` qua **Git Bash** hoặc **WSL** (PowerShell không chạy trực tiếp các script bash).

## 1. Setup một lần

Từ **root** repository:

```bash
./dev/setup
```

Script sẽ:

- Copy `api/.env.example` → `api/.env`
- Copy `web/.env.example` → `web/.env.local`
- Copy `docker/middleware.env.example` → `docker/middleware.env`
- Cài dependency (`uv sync`, `pnpm install`)

### Chỉnh file env sau setup

| File | Việc cần làm |
| --- | --- |
| `api/.env` | Đổi `SECRET_KEY` (xem [api/README.md](../api/README.md)) |
| `web/.env.local` | Giữ `NEXT_PUBLIC_API_PREFIX=http://localhost:5001/console/api` và `NEXT_PUBLIC_PUBLIC_API_PREFIX=http://localhost:5001/api` |
| `docker/middleware.env` | Thường giữ mặc định cho dev |

## 2. Chạy middleware (Docker)

```bash
./dev/start-docker-compose
```

Chỉ bật PostgreSQL, Redis, Weaviate (file `docker/docker-compose.middleware.yaml`), **không** chạy api/web container — tránh trùng cổng 5001/3000.

## 3. Chạy API, Web, Worker

Mở **3 terminal** (hoặc tmux), từ root:

```bash
./dev/start-api      # Flask :5001 + migration
./dev/start-web      # Next.js :3000
./dev/start-worker   # Celery (bắt buộc cho indexing, workflow async)
```

Tuỳ chọn lịch:

```bash
./dev/start-beat
```

Truy cập: **http://localhost:3000** (không qua nginx port 80).

## 4. So sánh Docker full vs dev local

| | Docker full (`docker compose up`) | Dev local |
| --- | --- | --- |
| UI | http://localhost (nginx :80) | http://localhost:3000 |
| API | Qua nginx / nội bộ container | http://localhost:5001 |
| Sửa code | Cần `--build` | Tự reload (web) / debug (api) |
| Phù hợp | Demo, QA, deploy | Lập trình hàng ngày |

## 5. Lệnh chất lượng code

```bash
# API (từ api/)
uv run pytest tests/unit_tests/
./dev/reformat

# Web (từ root)
pnpm -C web test
pnpm -C web lint:fix
```

Chi tiết: [AGENTS.md](../AGENTS.md), [web/docs/test.md](../web/docs/test.md).

## 6. Dừng middleware

```bash
cd docker
docker compose --env-file middleware.env -f docker-compose.middleware.yaml -p dify down
```

Project name `-p dify` khớp với `dev/start-docker-compose`.
