'use client'

import type { INavSelectorProps } from './nav-selector'
import * as React from 'react'
import { useState } from 'react'
import { useStore as useAppStore } from '@/app/components/app/store'
import { ArrowNarrowLeft } from '@/app/components/base/icons/src/vender/line/arrows'
import Link from '@/next/link'
import { useSelectedLayoutSegment } from '@/next/navigation'
import { cn } from '@/utils/classnames'
import { useConsoleNavLayout } from '../console-nav-layout-context'
import NavSelector from './nav-selector'

type INavProps = {
  icon: React.ReactNode
  activeIcon?: React.ReactNode
  text: string
  activeSegment: string | string[]
  link: string
  isApp: boolean
} & INavSelectorProps

const Nav = ({
  icon,
  activeIcon,
  text,
  activeSegment,
  link,
  curNav,
  navigationItems,
  createText,
  onCreate,
  onLoadMore,
  isLoadingMore,
  isApp,
}: INavProps) => {
  const { orientation } = useConsoleNavLayout()
  const isVertical = orientation === 'vertical'
  const setAppDetail = useAppStore(state => state.setAppDetail)
  const [hovered, setHovered] = useState(false)
  const segment = useSelectedLayoutSegment()
  const isActivated = Array.isArray(activeSegment) ? activeSegment.includes(segment!) : segment === activeSegment
  const isVerticalExpanded = isVertical && isActivated && !!curNav

  return (
    <div
      className={cn(
        'flex shrink-0 rounded-xl text-sm font-medium',
        isVertical
          ? cn(
              'relative w-full flex-col items-stretch rounded-xl border border-transparent px-0',
              isVerticalExpanded ? 'gap-0 overflow-hidden py-0' : 'gap-1 py-1',
              isActivated
                && 'border-divider-regular bg-state-base-hover font-semibold shadow-none border-r-[3px] border-r-text-accent',
              !isActivated && !curNav && 'hover:bg-state-base-hover',
            )
          : cn(
              'h-8 max-w-[670px] items-center px-0.5 max-[1024px]:max-w-[400px]',
              isActivated && 'bg-components-main-nav-nav-button-bg-active font-semibold shadow-md',
              !curNav && !isActivated && 'hover:bg-components-main-nav-nav-button-bg-hover',
            ),
      )}
    >
      <Link href={link} className={cn(isVertical && 'min-w-0 w-full')}>
        <div
          onClick={(e) => {
            // Don't clear state if opening in new tab/window
            if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0)
              return
            setAppDetail()
          }}
          className={cn(
            'flex cursor-pointer items-center gap-2 rounded-lg',
            isVertical ? cn('h-9 w-full min-w-0 px-3', isVerticalExpanded && 'rounded-none') : 'h-7 rounded-lg px-2.5',
            isActivated && isVertical && 'text-text-primary',
            isActivated && !isVertical && 'text-components-main-nav-nav-button-text-active',
            !isActivated && isVertical && 'text-text-secondary',
            !isActivated && !isVertical && 'text-components-main-nav-nav-button-text',
            curNav && isActivated && !isVertical && 'hover:bg-components-main-nav-nav-button-bg-active-hover',
            curNav && isActivated && isVertical && 'hover:bg-state-base-hover',
          )}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          <div className="flex h-4 w-4 shrink-0 items-center justify-center">
            {
              (hovered && curNav)
                ? <ArrowNarrowLeft className="h-4 w-4" />
                : isActivated
                  ? activeIcon
                  : icon
            }
          </div>
          <span className={cn(isVertical ? 'min-w-0 flex-1 truncate' : 'ml-2 truncate', !isVertical && 'max-[1024px]:hidden')}>
            {text}
          </span>
        </div>
      </Link>
      {
        curNav && isActivated && (
          <>
            {!isVertical && <div className="font-light text-divider-deep">/</div>}
            {isVertical && <div className="w-full shrink-0 border-0 border-t border-divider-regular" />}
            <div className={cn(isVertical && 'min-w-0', isVerticalExpanded ? 'px-0 pb-1' : 'px-0.5 pb-0.5')}>
              <NavSelector
                isApp={isApp}
                curNav={curNav}
                navigationItems={navigationItems}
                createText={createText}
                onCreate={onCreate}
                onLoadMore={onLoadMore}
                isLoadingMore={isLoadingMore}
              />
            </div>
          </>
        )
      }
    </div>
  )
}

export default Nav
