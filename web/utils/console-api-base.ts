import { env } from '@/env'
import { isClient } from '@/utils/client'

/**
 * Resolves the console API base as an absolute URL ending with `/`, suitable for
 * `new URL(relativePath, base)` or string concatenation after stripping the trailing slash.
 *
 * When `NEXT_PUBLIC_BASE_PATH` is set and `NEXT_PUBLIC_API_PREFIX` is a root-relative path
 * that does not already include that base path, the base path is prepended so browser
 * requests stay under the same deployment prefix (cookies, nginx routing).
 *
 * If the API lives at the host root while the app uses a base path, set
 * `NEXT_PUBLIC_API_PREFIX` to an absolute URL (https://host/console/api) so this helper
 * does not prepend the base path.
 */
export function resolveConsoleApiBaseHref(apiPrefix: string): string {
  let trimmed = apiPrefix.trim().replace(/\/$/, '')
  const bp = (env.NEXT_PUBLIC_BASE_PATH || '').trim().replace(/\/$/, '')
  if (
    bp
    && !trimmed.startsWith('http://')
    && !trimmed.startsWith('https://')
    && trimmed.startsWith('/')
    && trimmed !== bp
    && !trimmed.startsWith(`${bp}/`)
  )
    trimmed = `${bp}${trimmed}`.replace(/\/$/, '')

  if (trimmed.startsWith('http://') || trimmed.startsWith('https://'))
    return `${trimmed}/`

  const rel = trimmed.startsWith('/') ? trimmed : `/${trimmed}`
  if (isClient)
    return `${new URL(rel, window.location.origin).href.replace(/\/$/, '')}/`

  return `${rel.replace(/\/$/, '')}/`
}
