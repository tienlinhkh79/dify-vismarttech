'use client'
import * as React from 'react'
import { useState } from 'react'
import { useEventEmitterContextContext } from '@/context/event-emitter'
import useBreakpoints, { MediaType } from '@/hooks/use-breakpoints'
import { usePathname } from '@/next/navigation'
import { cn } from '@/utils/classnames'
import s from './index.module.css'

type HeaderWrapperProps = {
  children: React.ReactNode
}

const HeaderWrapper = ({
  children,
}: HeaderWrapperProps) => {
  const pathname = usePathname()
  const media = useBreakpoints()
  const isMobile = media === MediaType.mobile
  const isBordered = ['/apps', '/datasets/create', '/tools'].includes(pathname)
  // Check if the current path is a workflow canvas & fullscreen
  const inWorkflowCanvas = pathname.endsWith('/workflow')
  const isPipelineCanvas = pathname.endsWith('/pipeline')
  const workflowCanvasMaximize = localStorage.getItem('workflow-canvas-maximize') === 'true'
  const [hideHeader, setHideHeader] = useState(workflowCanvasMaximize)
  const { eventEmitter } = useEventEmitterContextContext()

  eventEmitter?.useSubscription((v: any) => {
    if (v?.type === 'workflow-canvas-maximize')
      setHideHeader(v.payload)
  })

  return (
    <div
      className={cn(
        'z-30 flex shrink-0 flex-col',
        s.header,
        isMobile
          ? cn(
              'sticky left-0 right-0 top-0 min-h-[56px] grow-0 basis-auto',
              isBordered && 'border-b border-divider-regular',
            )
          : cn(
              'sticky top-0 h-screen w-[280px] border-r border-divider-regular bg-background-body shadow-sm',
            ),
        hideHeader && (inWorkflowCanvas || isPipelineCanvas) && 'hidden',
      )}
    >
      {children}
    </div>
  )
}
export default HeaderWrapper
