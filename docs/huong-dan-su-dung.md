# Hướng dẫn sử dụng

Sau khi chạy Docker và hoàn tất [Bắt đầu nhanh](./bat-dau-nhanh.md), bạn đăng nhập console **Vismarttech** tại http://localhost.

## Giao diện chính

| Khu vực | Đường dẫn | Mục đích |
| --- | --- | --- |
| **Ứng dụng (Apps)** | `/apps` | Tạo chatbot, workflow, agent |
| **Knowledge / Datasets** | `/datasets` | Upload tài liệu, RAG |
| **Omnichannel** | `/omnichannel` | Hộp thư đa kênh (Zalo, v.v.) |
| **Mini CRM** | `/mini-crm` | Quản lý lead/khách hàng (nếu đã bật) |
| **Công cụ / Plugins** | `/tools`, `/plugins` | Tool và plugin |
| **Cài đặt workspace** | Biểu tượng workspace → Settings | Model, thành viên, kênh |

Thanh điều hướng có thể khác tuỳ quyền tài khoản.

## Luồng làm việc cơ bản

### 1. Cấu hình model (lần đầu)

1. Vào **Settings** → **Model provider**.
2. Thêm API key (OpenAI, Azure, hoặc provider bạn dùng).
3. Chọn model mặc định cho workspace.

Không cấu hình model → không chạy được app/workflow.

### 2. Tạo Knowledge (RAG)

1. **Datasets** → **Create dataset**.
2. Upload file (PDF, DOCX, …) hoặc nối nguồn đồng bộ.
3. Chờ indexing xong (trạng thái **Available**).

Worker Celery xử lý indexing — nếu treo lâu, kiểm tra container `worker`: `docker compose logs worker`.

### 3. Tạo ứng dụng

1. **Apps** → **Create app**.
2. Chọn loại: **Chatbot**, **Agent**, **Workflow**, v.v.
3. Trong app:
   - Gắn **Knowledge** đã tạo (nếu cần RAG).
   - Chỉnh prompt / workflow trên canvas.
4. **Publish** → lấy link chia sẻ hoặc nhúng API.

### 4. Omnichannel (hộp thư đa kênh)

1. Mở **Omnichannel** (`/omnichannel`).
2. Trong **Settings** (workspace): kết nối kênh (Zalo OA, v.v.) theo hướng dẫn trên UI.
3. Tin nhắn khách vào sẽ hiện danh sách hội thoại; chọn hội thoại để trả lời hoặc gán agent/app.

Tính năng phụ thuộc cấu hình backend (token kênh, webhook). Xem log `api` nếu không nhận tin.

### 5. API & tích hợp bên ngoài

- **Develop** trong từng app → API keys, curl mẫu.
- Base URL public API (self-host qua nginx): thường `http://localhost/api` (console hiển thị chính xác theo môi trường).

## Phân quyền

| Vai trò (tham khảo) | Quyền điển hình |
| --- | --- |
| Owner / Admin | Cấu hình workspace, model, kênh, thành viên |
| Editor | Sửa app, dataset |
| Normal | Dùng app được chia sẻ |

Chi tiết theo màn hình **Members** trong Settings.

## Môi trường và branding

- Tên hiển thị mặc định: **Vismarttech** (logo `web/public/logo/brand-logo-square.png`).
- Workspace có thể bật **custom branding** (logo, title) trong Settings nếu tính năng được bật trên server.

## Khi cần hỗ trợ kỹ thuật

1. Ghi lại thời điểm, URL, tài khoản (không gửi mật khẩu).
2. Đính kèm log: `docker compose logs api --tail=200` (trong `docker/`).
3. Nếu lỗi chỉ trên môi trường dev source → xem [Phát triển local](./phat-trien-local.md).
