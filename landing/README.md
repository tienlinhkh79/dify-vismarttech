# Vismarttech Landing

Marketing landing page, built with Next.js App Router and Tailwind CSS v4.

## Scripts

- `pnpm --filter dify-landing dev`
- `pnpm --filter dify-landing build`
- `pnpm --filter dify-landing start`

## Docker

- Service name: `landing` in `docker/docker-compose.yaml`
- Default host port: `3001`
- Open `http://localhost:3001`

## Branding

- Primary copy and site config: `content/site.ts`
- Design baseline: `design-system/MASTER.md`

## Notes

- Deployed separately from `web/` so marketing and the console can ship independently.
- Set `NEXT_PUBLIC_DIFY_APP_URL` in Docker env to the console URL for CTA links.
