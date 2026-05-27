'use client'

import type { INavSelectorProps } from './nav-selector'
import * as React from 'react'
import { useCallback, useState } from 'react'
import { useStore as useAppStore } from '@/app/components/app/store'
import { ArrowNarrowLeft } from '@/app/components/base/icons/src/vender/line/arrows'
import Link from '@/next/link'
import { useSelectedLayoutSegment } from '@/next/navigation'
import { cn } from '@/utils/classnames'
import { useConsoleNavLayout } from '../console-nav-layout-context'
import {
  consoleSidebarNavItemActiveVerticalAccentClass,
  consoleSidebarNavItemActiveVerticalClass,
  consoleSidebarNavItemClass,
} from '../console-nav-sidebar-item-class'
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

  const handleMainRowClick = useCallback((e: React.MouseEvent) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0)
      return
    setAppDetail()
  }, [setAppDetail])

  const verticalLinkClass = cn(
    consoleSidebarNavItemClass,
    isVerticalExpanded && 'rounded-t-lg rounded-b-none',
    isActivated && !isVerticalExpanded && consoleSidebarNavItemActiveVerticalClass,
    isActivated && isVerticalExpanded && consoleSidebarNavItemActiveVerticalAccentClass,
    !isActivated && 'text-text-secondary hover:bg-state-base-hover hover:text-text-primary',
    curNav && isActivated && 'hover:bg-state-base-hover',
  )

  const horizontalRowClass = cn(
    'flex h-7 cursor-pointer items-center gap-2 rounded-lg px-2.5 outline-none select-none',
    'focus-visible:ring-1 focus-visible:ring-components-input-border-hover focus-visible:outline-hidden focus-visible:ring-inset',
    isActivated && 'text-components-main-nav-nav-button-text-active',
    !isActivated && 'text-components-main-nav-nav-button-text',
    curNav && isActivated && 'hover:bg-components-main-nav-nav-button-bg-active-hover',
  )

  return (
    <div
      className={cn(
        'shrink-0 text-sm font-medium',
        isVertical
          ? cn(
              'relative flex w-full flex-col items-stretch overflow-hidden rounded-lg border border-transparent',
              isVerticalExpanded && 'gap-0 py-0',
            )
          : cn(
              'flex h-8 max-w-[670px] items-center rounded-xl px-0.5 max-[1024px]:max-w-[400px]',
              isActivated && 'bg-components-main-nav-nav-button-bg-active text-components-main-nav-nav-button-text-active shadow-md',
              !curNav && !isActivated && 'hover:bg-components-main-nav-nav-button-bg-hover',
            ),
      )}
    >
      <Link
        href={link}
        onClick={handleMainRowClick}
        className={cn(
          isVertical && cn('w-full min-w-0 no-underline', verticalLinkClass),
          !isVertical && 'flex min-w-0 items-center',
        )}
        onMouseEnter={isVertical ? () => setHovered(true) : undefined}
        onMouseLeave={isVertical ? () => setHovered(false) : undefined}
      >
        {isVertical
          ? (
              <>
                <div className="flex h-4 w-4 shrink-0 items-center justify-center">
                  {
                    (hovered && curNav)
                      ? <ArrowNarrowLeft className="h-4 w-4" />
                      : isActivated
                        ? activeIcon
                        : icon
                  }
                </div>
                <span className="min-w-0 flex-1 truncate">
                  {text}
                </span>
              </>
            )
          : (
              <div
                className={horizontalRowClass}
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
                <span className={cn('ml-2 truncate max-[1024px]:hidden')}>
                  {text}
                </span>
              </div>
            )}
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
