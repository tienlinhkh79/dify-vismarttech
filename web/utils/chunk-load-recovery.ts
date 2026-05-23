const RELOAD_KEY = 'chunk-load-reload-once'

const CHUNK_ERROR_PATTERNS = [
  /loading chunk/i,
  /chunkloaderror/i,
  /failed to fetch dynamically imported module/i,
  /importing a module script failed/i,
]

function isChunkLoadMessage(message: string): boolean {
  return CHUNK_ERROR_PATTERNS.some(pattern => pattern.test(message))
}

/**
 * After a deploy, cached HTML may reference removed /_next/ chunks.
 * Reload once when the browser reports a chunk load failure.
 */
export function installChunkLoadRecovery(): void {
  if (typeof window === 'undefined')
    return

  const reloadOnce = (reason: string) => {
    if (sessionStorage.getItem(RELOAD_KEY) === '1')
      return
    sessionStorage.setItem(RELOAD_KEY, '1')
    console.warn('[chunk-load-recovery] reloading after chunk failure:', reason)
    window.location.reload()
  }

  window.addEventListener('error', (event) => {
    const message = event.message || (event.error instanceof Error ? event.error.message : '')
    if (message && isChunkLoadMessage(message))
      reloadOnce(message)
  })

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    const message = reason instanceof Error ? reason.message : String(reason ?? '')
    if (isChunkLoadMessage(message))
      reloadOnce(message)
  })
}

export function clearChunkLoadRecoveryFlag(): void {
  try {
    sessionStorage.removeItem(RELOAD_KEY)
  }
  catch {
    /* ignore */
  }
}
