'use client'

import { useCallback, useState } from 'react'
import { RiArrowDownSLine } from '@remixicon/react'
import { useTranslation } from 'react-i18next'
import { Group } from '@/app/components/base/icons/src/vender/other'
import { Avatar } from '@/app/components/base/avatar'
import { toast } from '@/app/components/base/ui/toast'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLinkItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/app/components/base/ui/dropdown-menu'
import { Plan } from '@/app/components/billing/type'
import { AccountMenuPanel } from '@/app/components/header/account-dropdown/account-menu-panel'
import { ACCOUNT_SETTING_TAB } from '@/app/components/header/account-setting/constants'
import AccountAbout from '@/app/components/header/account-about'
import Indicator from '@/app/components/header/indicator'
import LicenseNav from '@/app/components/header/license-env'
import PlanBadge from '@/app/components/header/plan-badge'
import DownloadingIcon from '@/app/components/header/plugins-nav/downloading-icon'
import { usePluginTaskStatus } from '@/app/components/plugins/plugin-page/plugin-tasks/hooks'
import { useAppContext } from '@/context/app-context'
import { useWorkspacesContext } from '@/context/workspace-context'
import { useModalContext } from '@/context/modal-context'
import { useProviderContext } from '@/context/provider-context'
import Link from '@/next/link'
import { switchWorkspace } from '@/service/common'
import { cn } from '@/utils/classnames'
import { basePath } from '@/utils/var'

export type ConsoleHeroMenuTone = 'default' | 'onPrimary'

type ConsoleHeroMenuProps = {
  tone?: ConsoleHeroMenuTone
}

const ConsoleHeroMenu = ({ tone = 'default' }: ConsoleHeroMenuProps) => {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [aboutVisible, setAboutVisible] = useState(false)
  const { userProfile, langGeniusVersionInfo } = useAppContext()
  const { workspaces } = useWorkspacesContext()
  const currentWorkspace = workspaces.find(v => v.current)
  const { enableBilling, plan } = useProviderContext()
  const { setShowPricingModal, setShowAccountSettingModal } = useModalContext()
  const {
    isInstalling,
    isInstallingWithError,
    isFailed,
  } = usePluginTaskStatus()

  const isFreePlan = plan.type === Plan.sandbox
  const handlePlanClick = useCallback(() => {
    if (isFreePlan)
      setShowPricingModal()
    else
      setShowAccountSettingModal({ payload: ACCOUNT_SETTING_TAB.BILLING })
  }, [isFreePlan, setShowAccountSettingModal, setShowPricingModal])

  const isOnPrimary = tone === 'onPrimary'

  const handleSwitchWorkspace = async (tenant_id: string) => {
    try {
      if (currentWorkspace?.id === tenant_id)
        return
      await switchWorkspace({ url: '/workspaces/switch', body: { tenant_id } })
      toast.success(t('actionMsg.modifiedSuccessfully', { ns: 'common' }))
      setOpen(false)
      location.assign(`${location.origin}${basePath}`)
    }
    catch {
      toast.error(t('provider.saveFailed', { ns: 'common' }))
    }
  }

  return (
    <div className="flex min-w-0 shrink-0 items-center">
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger
          aria-label={t('account.account', { ns: 'common' })}
          className={cn(
            'flex max-w-[min(100vw-10rem,320px)] min-w-0 items-center gap-2 rounded-xl py-1 pl-1 pr-2 outline-none transition-colors',
            isOnPrimary
              ? cn(
                  'border border-white/20 bg-white/10 hover:border-white/35 hover:bg-white/15',
                  open && 'border-white/35 bg-white/15',
                )
              : cn(
                  'border border-divider-regular bg-components-input-bg-normal hover:border-divider-deep hover:bg-state-base-hover',
                  open && 'border-divider-deep bg-state-base-hover',
                ),
          )}
        >
          <Avatar avatar={userProfile.avatar_url} name={userProfile.name} size="lg" className="shrink-0" />
          <div className="min-w-0 flex-1 text-left">
            <div
              className={cn(
                'truncate system-sm-semibold',
                isOnPrimary ? 'text-white' : 'text-text-primary',
              )}
            >
              {userProfile.name}
            </div>
            <div
              className={cn(
                'truncate system-xs-regular',
                isOnPrimary ? 'text-white/70' : 'text-text-tertiary',
              )}
              title={currentWorkspace?.name}
            >
              {currentWorkspace?.name}
            </div>
          </div>
          {enableBilling && currentWorkspace && (
            <div
              className="shrink-0"
              onPointerDown={e => e.stopPropagation()}
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                handlePlanClick()
              }}
            >
              <PlanBadge allowHover sandboxAsUpgrade plan={currentWorkspace.plan as Plan} onClick={handlePlanClick} />
            </div>
          )}
          <RiArrowDownSLine
            className={cn('h-4 w-4 shrink-0', isOnPrimary ? 'text-white/70' : 'text-text-tertiary')}
            aria-hidden
          />
        </DropdownMenuTrigger>
        <DropdownMenuContent
          sideOffset={6}
          popupClassName="w-[min(100vw-2rem,380px)] max-w-[min(100vw-2rem,380px)] bg-components-panel-bg-blur! p-2! backdrop-blur-xs"
        >
          {!enableBilling && (
            <div className="mb-2 flex rounded-xl border border-divider-subtle bg-background-section-burn px-3 py-2">
              <LicenseNav />
            </div>
          )}
          <div className="mb-2 rounded-xl border border-divider-subtle bg-background-section-burn p-1.5">
            <div className="flex min-w-0 items-center gap-3 px-2 py-2">
              <Avatar avatar={userProfile.avatar_url} name={userProfile.name} size="xl" className="shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-text-primary system-md-semibold">
                  {userProfile.name}
                </div>
                <div className="truncate text-text-tertiary system-xs-regular">
                  {userProfile.email}
                </div>
              </div>
            </div>
            <div className="mx-2 my-1 border-t border-divider-subtle" />
            <div
              className="max-h-[180px] overflow-y-auto px-1"
              role="listbox"
              aria-label={t('userProfile.workspace', { ns: 'common' })}
            >
              {workspaces.map(workspace => (
                <DropdownMenuItem
                  key={workspace.id}
                  className={cn(
                    'cursor-pointer rounded-lg py-1.5 pl-2 pr-2',
                    currentWorkspace?.id === workspace.id && 'bg-state-base-hover',
                  )}
                  onClick={() => void handleSwitchWorkspace(workspace.id)}
                >
                  <div className="flex w-full min-w-0 items-center gap-2">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-components-icon-bg-blue-solid text-[13px]">
                      <span className="h-6 bg-gradient-to-r from-components-avatar-shape-fill-stop-0 to-components-avatar-shape-fill-stop-100 bg-clip-text align-middle font-semibold uppercase leading-6 text-shadow-shadow-1 opacity-90">
                        {workspace?.name[0]?.toLocaleUpperCase()}
                      </span>
                    </div>
                    <div className="line-clamp-1 min-w-0 grow text-left text-text-secondary system-md-regular">
                      {workspace.name}
                    </div>
                    {(!enableBilling || workspace.id !== currentWorkspace?.id) && (
                      <PlanBadge plan={workspace.plan as Plan} />
                    )}
                  </div>
                </DropdownMenuItem>
              ))}
            </div>
          </div>
          <div className="mb-2 rounded-xl border border-divider-subtle bg-background-section-burn p-1.5">
            <div className="px-2 pb-1 pt-0.5">
              <span className="text-text-tertiary system-xs-medium-uppercase">{t('menus.plugins', { ns: 'common' })}</span>
            </div>
            <DropdownMenuLinkItem
              className="justify-between rounded-lg"
              render={<Link href="/plugins" />}
            >
              <div className="relative flex w-full items-center gap-2">
                {(isFailed || isInstallingWithError) && (
                  <Indicator color="red" className="absolute -left-0.5 -top-0.5" />
                )}
                <div className="flex h-5 w-5 shrink-0 items-center justify-center text-text-secondary">
                  {(!(isInstalling || isInstallingWithError)) && <Group className="h-4 w-4" />}
                  {(isInstalling || isInstallingWithError) && <DownloadingIcon />}
                </div>
                <span className="system-sm-medium text-text-secondary">{t('menus.plugins', { ns: 'common' })}</span>
              </div>
            </DropdownMenuLinkItem>
          </div>
          <DropdownMenuSeparator className="my-1! bg-divider-subtle" />
          <AccountMenuPanel
            showProfile={false}
            closeMenu={() => setOpen(false)}
            onRequestAbout={() => {
              setAboutVisible(true)
              setOpen(false)
            }}
          />
        </DropdownMenuContent>
      </DropdownMenu>
      {aboutVisible && (
        <AccountAbout onCancel={() => setAboutVisible(false)} langGeniusVersionInfo={langGeniusVersionInfo} />
      )}
    </div>
  )
}

export default ConsoleHeroMenu
