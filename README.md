<p align="center">
  <img src="./web/public/logo/brand-logo-square.png" alt="Vismarttech" width="120" />
</p>

<h1 align="center">Vismarttech</h1>

<p align="center">
  Build production-ready agentic AI solutions — workflows, RAG, agents, and model management in one platform.
</p>

## Tài liệu

**Mới vào dự án → đọc ngay:** [docs/bat-dau-nhanh.md](./docs/bat-dau-nhanh.md) (Docker, cài đặt lần đầu, URL, xử lý sự cố).

| Tài liệu | Mô tả |
| --- | --- |
| [Bắt đầu nhanh](./docs/bat-dau-nhanh.md) | Clone → `docker compose up` → http://localhost/install |
| [Hướng dẫn sử dụng](./docs/huong-dan-su-dung.md) | Apps, datasets, omnichannel, model |
| [Phát triển local](./docs/phat-trien-local.md) | Chạy API/web từ source |
| [Mục lục docs](./docs/README.md) | Danh sách đầy đủ |

## Overview

**Vismarttech** là nền tảng AI self-hosted, fork từ [Dify](https://github.com/langgenius/dify), có branding, omnichannel inbox và tích hợp CRM.

| Area | Path | Stack |
| --- | --- | --- |
| Backend API | `api/` | Python, Flask, Celery |
| Frontend | `web/` | Next.js, TypeScript, React |
| Deployment | `docker/` | Docker Compose |

Quy ước phát triển: [AGENTS.md](./AGENTS.md).

## Quick start (Docker)

Yêu cầu: **2 CPU**, **4 GiB RAM**, [Docker](https://docs.docker.com/get-docker/) + Docker Compose.

```bash
cd docker
cp .env.example .env    # Windows: Copy-Item .env.example .env
docker compose up -d
```

Mở **http://localhost/install** để tạo tài khoản admin.

Chi tiết, biến môi trường và troubleshooting: **[docs/bat-dau-nhanh.md](./docs/bat-dau-nhanh.md)**.

## License

[Dify Open Source License](./LICENSE) (Apache 2.0 with additional conditions). Upstream Dify © LangGenius, Inc.
