FROM node:22-alpine AS base

RUN corepack enable
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

FROM base AS packages
WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml /app/
COPY landing/package.json /app/landing/

RUN corepack install
RUN VITE_GIT_HOOKS=0 pnpm install --filter ./landing... --no-frozen-lockfile

FROM base AS builder
WORKDIR /app
COPY --from=packages /app/ .
COPY . .

WORKDIR /app/landing
RUN pnpm build

FROM node:22-alpine AS production
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3001

WORKDIR /app
COPY --from=builder /app/landing/.next/standalone ./
COPY --from=builder /app/landing/.next/static ./landing/.next/static
RUN mkdir -p /app/landing/public
COPY ["Logo đơn giản - vuông 35x35cm.png", "/app/landing/public/vismarttech-logo.png"]

EXPOSE 3001
WORKDIR /app/landing
CMD ["node", "server.js"]
