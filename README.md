<p align="center">
  <img src="./web/public/logo/brand-logo-square.png" alt="Vismarttech" width="120" />
</p>

<h1 align="center">Vismarttech</h1>

<p align="center">
  Build production-ready agentic AI solutions — workflows, RAG, agents, and model management in one platform.
</p>

## Overview

**Vismarttech** is our self-hosted AI application platform. This repository extends the open-source [Dify](https://github.com/langgenius/dify) codebase with custom branding, omnichannel inbox, and CRM integrations tailored to our product.

| Area | Path | Stack |
| --- | --- | --- |
| Backend API | `api/` | Python, Flask, Celery |
| Frontend | `web/` | Next.js, TypeScript, React |
| Deployment | `docker/` | Docker Compose |

For day-to-day development conventions, see [AGENTS.md](./AGENTS.md).

## Quick start (Docker)

Minimum requirements: **2 CPU cores**, **4 GiB RAM**. Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).

```bash
cd docker
cp .env.example .env
docker compose up -d
```

Open [http://localhost/install](http://localhost/install) to finish setup.

## Local development

From the repository root:

```bash
./dev/setup
./dev/start-docker-compose   # PostgreSQL, Redis, vector DB
./dev/start-api
./dev/start-web
./dev/start-worker           # optional: async tasks
```

- Backend details: [api/README.md](./api/README.md)
- Frontend details: [web/README.md](./web/README.md)

## Configuration

Copy and edit environment files as needed:

- `docker/.env` — deployment
- `api/.env` — API service
- `web/.env.local` — console UI (from `web/.env.example`)

## License

This project inherits the [Dify Open Source License](./LICENSE) (Apache 2.0 with additional conditions). Upstream Dify is © LangGenius, Inc.
