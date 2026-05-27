'use client'

import { useAppContext } from '@/context/app-context'
import AppNav from './app-nav'
import { ConsoleNavLayoutProvider } from './console-nav-layout-context'
import { consoleSidebarNavItemClass } from './console-nav-sidebar-item-class'
import DatasetNav from './dataset-nav'
import EnvNav from './env-nav'
import ExploreNav from './explore-nav'
import MiniCrmNav from './mini-crm-nav'
import OmnichannelNav from './omnichannel-nav'
import ToolsNav from './tools-nav'

const ConsoleSidebarNav = () => {
  const { isCurrentWorkspaceEditor, isCurrentWorkspaceDatasetOperator, langGeniusVersionInfo } = useAppContext()
  const showEnvFooter = langGeniusVersionInfo.current_env === 'TESTING' || langGeniusVersionInfo.current_env === 'DEVELOPMENT'

  return (
    <ConsoleNavLayoutProvider orientation="vertical">
      <div className="flex h-full min-h-0 w-full min-w-0 flex-col">
        <nav className="min-h-0 w-full flex-1 space-y-1 overflow-x-hidden overflow-y-auto px-2 py-3">
          {!isCurrentWorkspaceDatasetOperator && <ExploreNav className={consoleSidebarNavItemClass} />}
          {!isCurrentWorkspaceDatasetOperator && <AppNav />}
          {(isCurrentWorkspaceEditor || isCurrentWorkspaceDatasetOperator) && <DatasetNav />}
          {!isCurrentWorkspaceDatasetOperator && <OmnichannelNav className={consoleSidebarNavItemClass} />}
          {!isCurrentWorkspaceDatasetOperator && <MiniCrmNav className={consoleSidebarNavItemClass} />}
          {!isCurrentWorkspaceDatasetOperator && <ToolsNav className={consoleSidebarNavItemClass} />}
        </nav>
        {showEnvFooter && (
          <div className="mt-auto shrink-0 border-t border-divider-regular px-3 py-3">
            <EnvNav />
          </div>
        )}
      </div>
    </ConsoleNavLayoutProvider>
  )
}

export default ConsoleSidebarNav
