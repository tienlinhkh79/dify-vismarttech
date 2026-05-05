# Dify Landing

Marketing landing page app for Dify, built with Next.js App Router and Tailwind CSS v4.

## Scripts

- `pnpm --filter dify-landing dev`
- `pnpm --filter dify-landing build`
- `pnpm --filter dify-landing start`

## Docker

- Service name: `landing` in `docker/docker-compose.yaml`
- Default host port: `3001`
- Open `http://localhost:3001`

## Branding Setup

- Primary branding content is centralized at `content/site.ts`
- To update business copy, plans, and contacts, edit this file first
- Design baseline is documented at `design-system/MASTER.md`

## Notes

- This app is intentionally separate from `web/` so marketing and product deployment can evolve independently.
- Update `NEXT_PUBLIC_DIFY_APP_URL` in Docker env to point CTA to your actual app domain.
