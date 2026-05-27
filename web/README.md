# Vismarttech Frontend

Next.js console for the Vismarttech platform (fork of the Dify web app).

## Getting Started

### Prerequisites

- [Node.js]
- [pnpm]

Recommended: enable [Corepack] for consistent package manager versions.

```bash
npm install -g corepack
corepack enable
```

### Install and run

From the repository root:

```bash
pnpm install
cp web/.env.example web/.env.local
```

Set `NEXT_PUBLIC_API_PREFIX` and `NEXT_PUBLIC_PUBLIC_API_PREFIX` to your API URL. If frontend and API use different subdomains, set `NEXT_PUBLIC_COOKIE_DOMAIN=1` and keep both under the same registrable domain.

```bash
pnpm -C web run dev
# or: pnpm -C web run dev:vinext
```

Open <http://localhost:3000>.

## Production build

```bash
pnpm -C web run build
pnpm -C web run start
```

Docker image (build from repo root):

```bash
docker build -f web/Dockerfile -t vismarttech-web .
```

## Quality

- Lint: see [web/docs/lint.md]
- Tests: see [web/docs/test.md]

```bash
pnpm -C web test
pnpm -C web storybook
```

[Corepack]: https://github.com/nodejs/corepack#readme
[Node.js]: https://nodejs.org
[pnpm]: https://pnpm.io
[web/docs/lint.md]: ./docs/lint.md
[web/docs/test.md]: ./docs/test.md
