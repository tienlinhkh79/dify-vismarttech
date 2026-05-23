'use client'

import { useCallback } from 'react'
import ConsoleBrandedLogo from '@/app/components/header/console-branded-logo'
import { APP_DISPLAY_NAME } from '@/config/app-display-name'
import WorkplaceSelector from '@/app/components/header/account-dropdown/workplace-selector'
import { ACCOUNT_SETTING_TAB } from '@/app/components/header/account-setting/constants'
import { useAppContext } from '@/context/app-context'
import { useGlobalPublicStore } from '@/context/global-public-context'
import { useModalContext } from '@/context/modal-context'
import { useProviderContext } from '@/context/provider-context'
import { WorkspaceProvider } from '@/context/workspace-context-provider'
import Link from '@/next/link'
import { Plan } from '../billing/type'
import { cn } from '@/utils/classnames'
import AccountDropdown from './account-dropdown'
import AppNav from './app-nav'
import { ConsoleNavLayoutProvider } from './console-nav-layout-context'
import DatasetNav from './dataset-nav'
import ExploreNav from './explore-nav'
import LicenseNav from './license-env'
import MiniCrmNav from './mini-crm-nav'
import OmnichannelNav from './omnichannel-nav'
import PlanBadge from './plan-badge'
import PluginsNav from './plugins-nav'
import ToolsNav from './tools-nav'
import s from './index.module.css'

const navClassName = `
  flex items-center relative px-3 h-8 rounded-xl
  font-medium text-sm
  cursor-pointer
`

const MobileConsoleHeader = () => {
  const { isCurrentWorkspaceEditor, isCurrentWorkspaceDatasetOperator } = useAppContext()
  const { enableBilling, plan } = useProviderContext()
  const { setShowPricingModal, setShowAccountSettingModal } = useModalContext()
  const systemFeatures = useGlobalPublicStore(s => s.systemFeatures)
  const isFreePlan = plan.type === Plan.sandbox
  const isBrandingEnabled = systemFeatures.branding.enabled
  const handlePlanClick = useCallback(() => {
    if (isFreePlan)
      setShowPricingModal()
    else
      setShowAccountSettingModal({ payload: ACCOUNT_SETTING_TAB.BILLING })
  }, [isFreePlan, setShowAccountSettingModal, setShowPricingModal])

  const renderLogo = () => (
    <h1>
      <Link
        href="/apps"
        className="flex h-10 shrink-0 cursor-pointer items-center justify-center gap-2 overflow-hidden px-0.5"
      >
        <span className="sr-only">
          {isBrandingEnabled && systemFeatures.branding.application_title ? systemFeatures.branding.application_title : APP_DISPLAY_NAME}
        </span>
        <ConsoleBrandedLogo size="large" />
      </Link>
    </h1>
  )

  return (
    <ConsoleNavLayoutProvider orientation="horizontal">
      <div className="">
        <div className={cn('flex items-center justify-between px-2 py-2', s.consoleTopBarMobile)}>
          <div className="flex min-w-0 flex-1 items-center">
            {renderLogo()}
            <div className="mx-1.5 shrink-0 font-light text-white/40">/</div>
            <WorkspaceProvider>
              <WorkplaceSelector tone="onPrimary" />
            </WorkspaceProvider>
            {enableBilling ? <PlanBadge allowHover sandboxAsUpgrade plan={plan.type} onClick={handlePlanClick} /> : <LicenseNav />}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <PluginsNav tone="onPrimary" />
            <AccountDropdown tone="onPrimary" />
          </div>
        </div>
        <div className="my-1 flex items-center justify-center space-x-1">
          {!isCurrentWorkspaceDatasetOperator && <ExploreNav className={navClassName} />}
          {!isCurrentWorkspaceDatasetOperator && <AppNav />}
          {(isCurrentWorkspaceEditor || isCurrentWorkspaceDatasetOperator) && <DatasetNav />}
          {!isCurrentWorkspaceDatasetOperator && <OmnichannelNav className={navClassName} />}
          {!isCurrentWorkspaceDatasetOperator && <MiniCrmNav className={navClassName} />}
          {!isCurrentWorkspaceDatasetOperator && <ToolsNav className={navClassName} />}
        </div>
      </div>
    </ConsoleNavLayoutProvider>
  )
}

export default MobileConsoleHeader
