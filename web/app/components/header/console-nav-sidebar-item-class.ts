import { cn } from '@/utils/classnames'

/** Shared vertical rail: 8px grid, no asymmetric border that shifts layout on active */
export const consoleSidebarNavItemClass = cn(
  'flex min-h-10 w-full shrink-0 cursor-pointer items-center gap-2 rounded-lg border border-transparent px-3 py-2',
  'text-sm font-medium transition-colors select-none outline-none',
  'focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-components-input-border-hover',
)

/** Active row: left accent bar only (no mixed pill background + edge bar). */
export const consoleSidebarNavItemActiveVerticalClass =
  "relative text-text-primary before:absolute before:inset-y-2 before:left-0 before:block before:w-[3px] before:rounded-r-full before:bg-text-accent before:content-['']"

/** Same left accent when the nav row sits inside an expanded group container. */
export const consoleSidebarNavItemActiveVerticalAccentClass = consoleSidebarNavItemActiveVerticalClass

/** Route links in the console sidebar / mobile strip (pill + accent when vertical). */
export function cnConsoleSidebarRouteNavLink(
  passedClassName: string | undefined,
  options: { activated: boolean, isVertical: boolean },
): string {
  const { activated, isVertical } = options
  return cn(
    passedClassName,
    'group',
    activated && isVertical && consoleSidebarNavItemActiveVerticalClass,
    activated && !isVertical && 'bg-components-main-nav-nav-button-bg-active text-components-main-nav-nav-button-text-active shadow-md',
    !activated && isVertical && 'text-text-secondary hover:bg-state-base-hover hover:text-text-primary',
    !activated && !isVertical && 'text-components-main-nav-nav-button-text hover:bg-components-main-nav-nav-button-bg-hover',
  )
}
