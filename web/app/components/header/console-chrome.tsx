'use client'

import { useState } from 'react'
import { useEventEmitterContextContext } from '@/context/event-emitter'
import useBreakpoints, { MediaType } from '@/hooks/use-breakpoints'
import { usePathname } from '@/next/navigation'
import { cn } from '@/utils/classnames'
import ConsoleSidebarNav from './console-sidebar-nav'
import ConsoleTopBar from './console-top-bar'
import MobileConsoleHeader from './mobile-console-header'
import ZaloOAuthReturnHandler from './zalo-oauth-return-handler'

type ConsoleChromeProps = {
  children: React.ReactNode
}

const ConsoleChrome = ({
  children,
}: ConsoleChromeProps) => {
  const pathname = usePathname()
  const media = useBreakpoints()
  const isMobile = media === MediaType.mobile
  const isBordered = ['/apps', '/datasets/create', '/tools'].includes(pathname)
  const inWorkflowCanvas = pathname.endsWith('/workflow')
  const isPipelineCanvas = pathname.endsWith('/pipeline')
  const workflowCanvasMaximize = typeof window !== 'undefined' && localStorage.getItem('workflow-canvas-maximize') === 'true'
  const [hideChrome, setHideChrome] = useState(workflowCanvasMaximize)
  const { eventEmitter } = useEventEmitterContextContext()

  eventEmitter?.useSubscription((v: any) => {
    if (v?.type === 'workflow-canvas-maximize')
      setHideChrome(v.payload)
  })

  if (isMobile) {
    return (
      <>
        <ZaloOAuthReturnHandler />
        <div
          className={cn(
            'z-30 flex min-h-screen w-full flex-col bg-background-body',
            hideChrome && (inWorkflowCanvas || isPipelineCanvas) && 'min-h-screen',
          )}
        >
          <div
            className={cn(
              'shrink-0',
              hideChrome && (inWorkflowCanvas || isPipelineCanvas) && 'hidden',
              !hideChrome && 'sticky left-0 right-0 top-0 z-30',
              isBordered && 'border-b border-divider-regular',
            )}
          >
            <MobileConsoleHeader />
          </div>
          <div className="flex min-h-0 min-w-0 flex-1 flex-col">
            {children}
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <ZaloOAuthReturnHandler />
      <div
        className={cn(
          'z-30 flex min-h-screen w-full flex-col bg-background-body',
        )}
      >
        <div
          className={cn(
            'sticky top-0 z-40 w-full shrink-0',
            hideChrome && (inWorkflowCanvas || isPipelineCanvas) && 'hidden',
          )}
        >
          <ConsoleTopBar />
        </div>
        <div className="flex min-h-0 min-w-0 flex-1 flex-row overflow-hidden">
          <aside
            className={cn(
              'h-[calc(100vh-3.5rem)] w-[240px] shrink-0 self-start border-r border-divider-regular bg-components-panel-bg md:sticky md:top-14',
              hideChrome && (inWorkflowCanvas || isPipelineCanvas)
                ? 'hidden'
                : 'hidden md:flex',
            )}
          >
            <ConsoleSidebarNav />
          </aside>
          <div className="flex min-h-0 min-w-0 flex-1 flex-col">
            {children}
          </div>
        </div>
      </div>
    </>
  )
}

export default ConsoleChrome
