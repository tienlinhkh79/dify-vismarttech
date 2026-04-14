# Chạy Dify từ fork đang customize (`web/` build local)

Fork này **cố định** dùng service `web` build từ source trong repo (`dify-web:local`, `pull_policy: never`). Đây là workflow bạn dùng hằng ngày; không kéo image frontend có sẵn từ Docker Hub cho `web`.

Khi sau này bạn `git pull` / merge từ upstream Dify: nếu `docker-compose.yaml` (hoặc template) xung đột ở block `web`, **giữ** cách fork — `build` + `context: ..` + `dockerfile: web/Dockerfile` + `image: dify-web:local` + `pull_policy: never` — để vẫn chạy bản custom.

---

**(Chỉ tham khảo — không áp dụng trong fork này)** Bản gốc Dify thường khai báo `web` chỉ với `image: langgenius/dify-web:<phiên_bản>` (không `build:`). Upstream đổi tag/image khi release; bạn chỉ cần biết để đối chiếu lúc merge, không cần bật lại trừ khi bạn chủ động bỏ custom và quay về image chính thức.

Logo console / “powered by” mặc định lấy từ **`web/public/logo/logo.png`** (fork này không còn để branding server `workspace_logo` đè lên).

## 1. Chuẩn bị

- Docker Desktop (Windows) bật sẵn.
- Vào thư mục compose:

```powershell
cd đường-dẫn-tới-repo\dify\docker
```

- Tạo file môi trường nếu chưa có (chỉnh theo máy bạn):

```powershell
copy .env.example .env
# sửa .env cho đúng URL/API nếu cần
```

## 2. Build frontend từ code của bạn

**Bắt buộc** trước lần chạy đầu, và **mỗi khi** đổi code trong `web/`.

Trên **Windows**, chạy (tránh lỗi BuildKit với `docker/volumes`). Script **vừa build vừa tạo lại container `web`** (`--force-recreate`), tránh trường hợp image mới nhưng container vẫn chạy bản cũ.

Nếu máy báo *running scripts is disabled* (Execution Policy), dùng **`build-web.cmd`** — nó gọi PowerShell với `-ExecutionPolicy Bypass` chỉ cho lệnh này:

```powershell
.\build-web.cmd
```

Chỉ build, **không** restart container `web` (hiếm khi cần):

```powershell
.\build-web.cmd -SkipUp
```

Nếu đổi `web/` rồi mà UI vẫn y như cũ: Docker có thể đang dùng **cache layer** — ép build sạch rồi script vẫn sẽ recreate container:

```powershell
.\build-web.cmd --no-cache
```

(Cách tương đương không cần `.cmd`: `powershell -NoProfile -ExecutionPolicy Bypass -File .\build-web.ps1`.)

Sau đó thử **Ctrl+F5** trên trình duyệt (tránh cache JS).

Trên Linux/macOS (hoặc PowerShell nếu không gặp lỗi context):

```bash
docker compose build web
docker compose up -d --force-recreate --no-deps web
```

## 3. Chạy toàn bộ stack

```powershell
docker compose up -d
```

Xem log web nếu cần:

```powershell
docker compose logs -f web
```

## 4. Sau khi chỉnh lại `web/`

```powershell
.\build-web.cmd
```

(Không cần thêm `docker compose up -d web` riêng trừ khi bạn dùng `-SkipUp` — script đã recreate service `web`.)

Các service khác (api, db, …) vẫn dùng image có sẵn trên Docker Hub như trong `docker-compose.yaml`, trừ **`web`** là bản build local (`dify-web:local`).

## 5. Đã build xong mà vẫn “không được” (UI không đổi / sai bản)

Trong thư mục `docker`, có thể gom nhanh:

```powershell
.\verify-stack.cmd
```

Hoặc từng lệnh:

```powershell
docker compose ps
docker compose images web
```

- **`web` không chạy hoặc Restarting** → xem `docker compose logs --tail=100 web`.
- **Image của `web` không phải `dify-web:local`** → bạn không đang dùng stack build từ repo này; kiểm tra đúng thư mục `cd` và file `.env`.
- **Hai bản Dify khác nhau cùng máy**: tên project Compose mặc định thường là `docker` — dễ trùng giữa các clone. Trong `.env` đặt **`COMPOSE_PROJECT_NAME`** duy nhất (ví dụ `dify-chatbot`), rồi `docker compose down` ở stack cũ (nếu cần) và `docker compose up -d` lại từ clone đúng.
- **`.env` trỏ nhầm sang domain khác** (`CONSOLE_WEB_URL`, `APP_WEB_URL`, …) → trình duyệt có thể mở bản cloud thay vì máy bạn; để trống hoặc `http://localhost` cho self-host.
- **Đúng stack nhưng vẫn thấy UI cũ**: thử cửa sổ ẩn danh hoặc xóa cache site; Next có thể cache mạnh ở trình duyệt.

Kiểm tra nhanh container `web` có đang chạy image vừa build (so sánh digest):

```powershell
docker images --digests dify-web:local
docker compose ps -q web | ForEach-Object { docker inspect $_ --format "{{.Image}} created {{.State.StartedAt}}" }
```

Nếu cần gỡ image cũ rồi build lại (ít khi cần):

```powershell
docker compose down
docker rmi dify-web:local
.\build-web.cmd --no-cache
docker compose up -d
```

### Lỗi khi build `web` (Windows)

- **`the --chmod option requires BuildKit`**: script build dùng `DOCKER_BUILDKIT=0`; `web/Dockerfile` đã tách `chmod` ra `RUN` để tương thích. Kéo bản `web/Dockerfile` mới nhất rồi build lại.
- **`Can't add file ... to tar: io: read/write on closed pipe`**: lỗi gửi context tạm thời — đóng build/build khác đang chạy, thử lại `.\build-web.cmd --no-cache`; nếu vẫn lỗi, tạm tắt quét real-time của antivirus trên thư mục repo hoặc thêm repo vào exclusion.
