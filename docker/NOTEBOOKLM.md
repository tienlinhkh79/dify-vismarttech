# NotebookLM Knowledge Source (Docker Profile: notebooklm)

NotebookLM tích hợp Google NotebookLM làm nguồn **External Knowledge** cho Dify Knowledge / Workflow **Knowledge Retrieval** nodes, đồng thời tự động nhận diện và đính kèm hình ảnh thiết kế từ NotebookLM Studio trả thẳng về cho người dùng (Zalo, Webchat, Messenger).

---

## 1. Cơ chế hoạt động (100% trong Docker)

Toàn bộ hệ thống chạy ngầm trong Docker containers, có chính sách `restart: unless-stopped`. **Mỗi khi khởi động lại máy, Docker Desktop tự động khởi động lại tất cả các container này, bạn không cần phải mở PowerShell hay chạy tiến trình thủ công nào trên Windows.**

```text
Dify Knowledge Retrieval Node (api container)
    │
    ▼
notebooklm-retrieval-proxy (Port 8080)
    │
    ├─► notebooklm-mcp (Port 8010, gemini-notebook-mcp-cli)
    │       └─► Google NotebookLM API
    │
    └─► Xử lý câu trả lời & đính kèm ảnh:
            - Lọc bỏ các câu hướng dẫn thừa: "(click ở bảng Studio bên phải màn hình)"
            - Nhận diện các tệp ảnh thiết kế (square_garden_villa.png, v.v.)
            - Nhúng Markdown ảnh: ![Tên ảnh](https://chatbotai.vismarttech.com/notebooklm-images/{tên_ảnh})
            - Phục vụ file tĩnh qua Nginx & endpoint /images/{filename}
```

---

## 2. Các Container trong hệ thống

| Container | Image | Port nội bộ | Vai trò |
|---|---|---|---|
| `docker-notebooklm-mcp-1` | `dify-notebooklm-mcp:local` | 8010 | MCP server kết nối Google NotebookLM (chạy `notebooklm-mcp-cli` v4.1.0) |
| `docker-notebooklm-retrieval-proxy-1` | `dify-notebooklm-retrieval-proxy:local` | 8080 | Proxy chuyển tiếp `/retrieval` chuẩn Dify, lọc văn bản & gắn link ảnh |
| `docker-nginx-1` | `nginx:latest` | 80, 443 | Định tuyến `https://chatbotai.vismarttech.com/notebooklm-images/` vào proxy |

---

## 3. Quản lý Docker (Khi bật/tắt máy)

Khi máy tính mở lại, Docker Desktop sẽ tự bật các container. Nếu cần bật/tắt hoặc kiểm tra trạng thái bằng lệnh:

```powershell
# Chuyển vào thư mục docker
cd C:\chatbot\dify\docker

# Khởi động cụm dịch vụ NotebookLM
docker compose --profile notebooklm up -d notebooklm-mcp notebooklm-retrieval-proxy nginx

# Xem log kiểm tra
docker compose logs -f notebooklm-retrieval-proxy
docker compose logs -f notebooklm-mcp
```

Hoặc bạn chỉ cần mở ứng dụng **Docker Desktop**, các container:
- `docker-notebooklm-mcp-1`
- `docker-notebooklm-retrieval-proxy-1`
- `docker-nginx-1`

đều hiển thị màu xanh lá (Running).

---

## 4. Thư mục lưu ảnh Studio

Ảnh từ NotebookLM Studio được mount trực tiếp vào Docker volume:
- Đường dẫn trên máy chủ Windows: `C:\chatbot\dify\docker\volumes\notebooklm_images\`
- Đường dẫn bên trong container: `/app/data/images`
- URL công khai tương ứng: `https://chatbotai.vismarttech.com/notebooklm-images/{tên_file}`

Nếu bạn thêm bất kỳ ảnh thiết kế mới nào vào thư mục `notebooklm_images`, proxy sẽ tự động nhận diện và gửi ảnh đó khi người dùng hỏi về dự án tương ứng.

---

## 5. Cấu hình trong Dify Knowledge

1. **Knowledge → External Knowledge API**:
   - **API Endpoint:** `http://notebooklm-retrieval-proxy:8080`
   - **API Key:** `sk-proj-1234567890` (hoặc giá trị trong biến `NOTEBOOKLM_PROXY_API_KEY` của file `docker/.env`)
2. **External Knowledge ID:**
   - Notebook UUID của bạn (ví dụ: `62135409-89d2-4bcc-9fd2-247bf40d0b35` cho "Square website docs")
3. Trong **Workflow / Chat App**:
   - Thêm node **Knowledge Retrieval** và chọn External Knowledge Dataset này.
