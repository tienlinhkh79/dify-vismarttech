'use client'

import { useTranslation } from 'react-i18next'
import { Group } from '@/app/components/base/icons/src/vender/other'
import Indicator from '@/app/components/header/indicator'
import { usePluginTaskStatus } from '@/app/components/plugins/plugin-page/plugin-tasks/hooks'
import Link from '@/next/link'
import { useSelectedLayoutSegment } from '@/next/navigation'
import { cn } from '@/utils/classnames'
import { useConsoleNavLayout } from '../console-nav-layout-context'
import DownloadingIcon from './downloading-icon'

type PluginsNavProps = {
  className?: string
  tone?: 'default' | 'onPrimary'
}

const PluginsNav = ({
  className,
  tone = 'default',
}: PluginsNavProps) => {
  const { t } = useTranslation()
  const { orientation } = useConsoleNavLayout()
  const isVertical = orientation === 'vertical'
  const selectedSegment = useSelectedLayoutSegment()
  const activated = selectedSegment === 'plugins'
  const {
    isInstalling,
    isInstallingWithError,
    isFailed,
  } = usePluginTaskStatus()

  const isOnPrimary = tone === 'onPrimary' && !isVertical

  return (
    <Link
      href="/plugins"
      className={cn(className, 'group', 'plugins-nav-button',
      // used for use-fold-anim-into.ts
        isVertical && 'block w-full min-w-0',
      )}
    >
      <div
        className={cn(
          'system-sm-medium relative flex flex-row items-center gap-0.5 rounded-xl border border-transparent p-1.5',
          isVertical ? 'h-auto min-h-9 w-full justify-start' : 'h-8 justify-center',
          activated && !isOnPrimary && 'border-components-main-nav-nav-button-border bg-components-main-nav-nav-button-bg-active text-components-main-nav-nav-button-text shadow-md',
          activated && isOnPrimary && 'border-white/30 bg-white/15 text-white shadow-md',
          !activated && !isOnPrimary && 'text-text-tertiary hover:bg-state-base-hover hover:text-text-secondary',
          !activated && isOnPrimary && 'text-white/75 hover:bg-white/10 hover:text-white',
          (isInstallingWithError || isFailed) && !activated && !isOnPrimary && 'border-components-panel-border-subtle',
          (isInstallingWithError || isFailed) && !activated && isOnPrimary && 'border-white/25',
        )}
      >
        {
          (isFailed || isInstallingWithError) && !activated && (
            <Indicator
              color="red"
              className="absolute -left-px -top-px"
            />
          )
        }
        <div className="mr-0.5 flex h-5 w-5 items-center justify-center">
          {
            (!(isInstalling || isInstallingWithError) || activated) && (
              <Group className="h-4 w-4" />
            )
          }
          {
            (isInstalling || isInstallingWithError) && !activated && (
              <DownloadingIcon />
            )
          }
        </div>
        <span className="px-0.5">{t('menus.plugins', { ns: 'common' })}</span>
      </div>
    </Link>
  )
}

export default PluginsNav
