'use client'

import type { LogoSize } from '@/app/components/base/logo/dify-logo'
import { APP_DISPLAY_NAME } from '@/config/app-display-name'
import { useGlobalPublicStore } from '@/context/global-public-context'
import { cn } from '@/utils/classnames'
import { basePath } from '@/utils/var'

const logoSizeMap: Record<LogoSize, string> = {
  large: 'h-10 w-auto max-w-[180px]',
  medium: 'h-8 w-auto max-w-[140px]',
  small: 'h-6 w-auto max-w-[100px]',
}

/** Bust browser cache after rebrand. */
const defaultConsoleLogoSrc = `${basePath}/logo/logo.png?v=vismarttech`

/**
 * Console header logo: enterprise branding URL when set, otherwise fork default in public/logo/logo.png.
 */
export function ConsoleBrandedLogo({
  size = 'large',
  className,
}: {
  size?: LogoSize
  className?: string
}) {
  const branding = useGlobalPublicStore(s => s.systemFeatures.branding)
  const brandedSrc = branding.enabled
    ? (branding.login_page_logo?.trim() || branding.workspace_logo?.trim() || '')
    : ''
  const src = brandedSrc || defaultConsoleLogoSrc

  return (
    <img
      src={src}
      className={cn('block object-contain', logoSizeMap[size], className)}
      alt={`${APP_DISPLAY_NAME} logo`}
      onError={(event) => {
        const img = event.currentTarget
        if (!img.dataset.fallbackApplied) {
          img.dataset.fallbackApplied = 'true'
          img.src = defaultConsoleLogoSrc
        }
      }}
    />
  )
}

export default ConsoleBrandedLogo
