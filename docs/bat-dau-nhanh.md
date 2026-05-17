# Bắt đầu nhanh

Tài liệu này dành cho lần đầu clone repo và chạy **toàn bộ hệ thống bằng Docker** — cách nhanh nhất để có môi trường dùng được.

## Yêu cầu

| Thành phần | Phiên bản tối thiểu |
| --- | --- |
| CPU | 2 core |
| RAM | 4 GiB (khuyến nghị 8 GiB+) |
| Docker | [Docker Desktop](https://docs.docker.com/get-docker/) hoặc Docker Engine |
| Docker Compose | Đi kèm Docker Desktop (lệnh `docker compose`) |

Trên Windows: bật **WSL 2** trong Docker Desktop để ổn định hơn.

## 1. Clone và vào thư mục

```bash
git clone <url-repo> dify
cd dify
```

## 2. Tạo file cấu hình Docker

```bash
cd docker
cp .env.example .env          # macOS / Linux / Git Bash
```

**Windows (PowerShell):**

```powershell
cd docker
Copy-Item .env.example .env
```

### Các biến nên chỉnh ngay (mở `docker/.env`)

| Biến | Gợi ý |
| --- | --- |
| `SECRET_KEY` | Chuỗi ngẫu nhiên dài (bắt buộc đổi trước production). Tạo nhanh: `openssl rand -base64 42` |
| `COMPOSE_PROJECT_NAME` | Đặt tên riêng nếu máy có nhiều stack Dify/Vismarttech (vd. `vismarttech-local`) — tránh trùng cổng/volume |
| `INIT_PASSWORD` | (Tuỳ chọn) Mật khẩu admin lúc cài đặt lần đầu |
| `EXPOSE_NGINX_PORT` | Mặc định `80`. Đổi nếu cổng 80 đã bị chiếm (vd. `8080`) |

Không cần sửa hết file `.env` — giá trị mặc định đủ cho dev local.

## 3. Khởi động stack

Vẫn trong thư mục `docker/`:

```bash
docker compose up -d
```

Lần đầu sẽ tải image — có thể mất vài phút.

### Kiểm tra container đang chạy

```bash
docker compose ps
```

Các service chính: `nginx`, `api`, `worker`, `web`, `db_postgres`, `redis`, `weaviate` (hoặc vector DB theo cấu hình).

### Xem log khi có lỗi

```bash
docker compose logs -f api
docker compose logs -f web
docker compose logs -f nginx
```

## 4. Khởi tạo lần đầu (Install wizard)

1. Mở trình duyệt: **http://localhost/install**  
   - Nếu đổi `EXPOSE_NGINX_PORT=8080` → dùng **http://localhost:8080/install**
2. Tạo tài khoản **Workspace owner** (email + mật khẩu).
3. Hoàn tất wizard → chuyển vào console.

Đăng nhập sau này: **http://localhost** (hoặc cổng bạn đã cấu hình).

## 5. URL mặc định

| Dịch vụ | URL (mặc định) | Ghi chú |
| --- | --- | --- |
| Console (UI chính) | http://localhost | Qua nginx |
| Cài đặt lần đầu | http://localhost/install | Chỉ chạy khi DB chưa có admin |
| Landing (marketing) | http://localhost:3001 | Service `landing`, tuỳ bật trong compose |
| API (trực tiếp, debug) | http://localhost:5001 | Thường không cần mở khi dùng qua nginx |

## 6. Lệnh Docker thường dùng

Chạy trong thư mục `docker/`:

```bash
# Dừng stack (giữ data)
docker compose stop

# Bật lại
docker compose start

# Dừng và gỡ container (vẫn giữ volume/data)
docker compose down

# Khởi động lại sau khi sửa .env
docker compose up -d

# Rebuild image sau khi pull code mới (nếu có thay đổi Dockerfile)
docker compose up -d --build
```

> **Cảnh báo:** `docker compose down -v` sẽ **xóa volume** (mất database). Chỉ dùng khi cố ý reset sạch.

## 7. Cập nhật code và chạy lại

```bash
git pull
cd docker
docker compose up -d --build
```

Migration database chạy tự động khi container `api` khởi động (`MIGRATION_ENABLED=true`).

## 8. Xử lý sự cố nhanh

| Triệu chứng | Cách xử lý |
| --- | --- |
| `localhost` không mở được | `docker compose ps` — đợi `api`, `web`, `nginx` healthy; xem `docker compose logs nginx` |
| Cổng 80 bị chiếm | Đặt `EXPOSE_NGINX_PORT=8080` trong `.env`, chạy lại `docker compose up -d` |
| Trang install lặp vô hạn | Kiểm tra `db_postgres` và `redis`; xem log `api` |
| Nhiều project Docker trùng nhau | Đặt `COMPOSE_PROJECT_NAME` unique trong `.env` |
| Đổi mật khẩu / quên admin | Reset volume DB (dev only) hoặc liên hệ người quản trị hạ tầng |

## Bước tiếp theo

- Dùng console: [Hướng dẫn sử dụng](./huong-dan-su-dung.md)
- Sửa code frontend/API: [Phát triển local](./phat-trien-local.md)
