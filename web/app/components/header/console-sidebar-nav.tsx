'use client'

import { useAppContext } from '@/context/app-context'
import { cn } from '@/utils/classnames'
import AppNav from './app-nav'
import { ConsoleNavLayoutProvider } from './console-nav-layout-context'
import DatasetNav from './dataset-nav'
import EnvNav from './env-nav'
import ExploreNav from './explore-nav'
import MiniCrmNav from './mini-crm-nav'
import OmnichannelNav from './omnichannel-nav'
import ToolsNav from './tools-nav'

/** Shared vertical rail: 8px grid, no asymmetric border that shifts layout on active */
export const consoleSidebarNavItemClass = cn(
  'flex min-h-10 w-full shrink-0 cursor-pointer items-center gap-2 rounded-lg border border-transparent px-3 py-2',
  'text-sm font-medium transition-colors',
)

const ConsoleSidebarNav = () => {
  const { isCurrentWorkspaceEditor, isCurrentWorkspaceDatasetOperator, langGeniusVersionInfo } = useAppContext()
  const showEnvFooter = langGeniusVersionInfo.current_env === 'TESTING' || langGeniusVersionInfo.current_env === 'DEVELOPMENT'

  return (
    <ConsoleNavLayoutProvider orientation="vertical">
      <div className="flex h-full min-h-0 w-full min-w-0 flex-col">
        <nav className="min-h-0 w-full flex-1 space-y-1 overflow-y-auto overflow-x-hidden px-2 py-3">
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
