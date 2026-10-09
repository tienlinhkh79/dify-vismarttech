'use client'

import { cn } from '@/utils/classnames'
import { getContactInitials, resolveStageTheme } from './crm-theme'

type CrmContactAvatarProps = {
  name: string
  stage?: string
  size?: 'sm' | 'md'
  className?: string
}

export function CrmContactAvatar({ name, stage, size = 'md', className }: CrmContactAvatarProps) {
  const theme = stage ? resolveStageTheme(stage) : null
  const sizeClass = size === 'sm' ? 'size-8 text-[10px]' : 'size-10 text-xs'

  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full font-semibold',
        sizeClass,
        className,
      )}
      style={{
        backgroundColor: theme?.bgColor ?? '#CCFBF1',
        color: theme?.color ?? '#0D9488',
        border: `1.5px solid ${theme?.borderColor ?? '#0D9488'}`,
      }}
      aria-hidden
    >
      {getContactInitials(name)}
    </div>
  )
}
