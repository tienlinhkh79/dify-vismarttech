'use client'

import { useCallback } from 'react'
import { RiSearchLine } from '@remixicon/react'
import { useTranslation } from 'react-i18next'
import ConsoleBrandedLogo from '@/app/components/header/console-branded-logo'
import { APP_DISPLAY_NAME } from '@/config/app-display-name'
import { useAppContext } from '@/context/app-context'
import { useGlobalPublicStore } from '@/context/global-public-context'
import { WorkspaceProvider } from '@/context/workspace-context-provider'
import Link from '@/next/link'
import { cn } from '@/utils/classnames'
import { ConsoleNavLayoutProvider } from './console-nav-layout-context'
import ConsoleHeroMenu from './console-hero-menu'
import s from './index.module.css'

const ConsoleTopBar = () => {
  const { t } = useTranslation('app')
  const { langGeniusVersionInfo } = useAppContext()
  const systemFeatures = useGlobalPublicStore(s => s.systemFeatures)
  const isBrandingEnabled = systemFeatures.branding.enabled
  const env = langGeniusVersionInfo.current_env
  const envHeaderClass = env === 'DEVELOPMENT'
    ? s['header-DEVELOPMENT']
    : env === 'TESTING'
      ? s['header-TESTING']
      : undefined

  const openCommandPalette = useCallback(() => {
    window.dispatchEvent(new CustomEvent('dify:open-goto-anything'))
  }, [])

  return (
    <ConsoleNavLayoutProvider orientation="horizontal">
      <header
        className={cn(
          'relative flex h-14 w-full shrink-0 items-center gap-4 px-4 text-white md:px-6',
          s.consoleTopBar,
          envHeaderClass,
        )}
      >
        <h1 className="shrink-0">
          <Link
            href="/apps"
            className="flex h-10 cursor-pointer items-center gap-2 overflow-hidden px-0.5"
          >
            <span className="sr-only">
              {isBrandingEnabled && systemFeatures.branding.application_title ? systemFeatures.branding.application_title : APP_DISPLAY_NAME}
            </span>
            <ConsoleBrandedLogo size="large" />
          </Link>
        </h1>
        <div className="flex min-w-0 flex-1 items-center justify-end gap-3">
          <button
            type="button"
            onClick={openCommandPalette}
            className={cn(
              'system-sm-regular flex min-h-9 min-w-0 max-w-xl flex-1 cursor-pointer items-center gap-2 rounded-lg border border-white/20',
              'bg-white/10 px-3 py-2 text-left text-white/80 transition-colors',
              'hover:border-white/35 hover:bg-white/15 hover:text-white',
            )}
          >
            <RiSearchLine className="h-4 w-4 shrink-0" aria-hidden />
            <span className="min-w-0 flex-1 truncate">{t('gotoAnything.searchPlaceholder')}</span>
          </button>
          <div className="flex min-w-0 shrink-0 items-center">
            <WorkspaceProvider>
              <ConsoleHeroMenu tone="onPrimary" />
            </WorkspaceProvider>
          </div>
        </div>
      </header>
    </ConsoleNavLayoutProvider>
  )
}

export default ConsoleTopBar
