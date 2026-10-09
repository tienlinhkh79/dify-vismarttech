'use client'

import type { MiniCrmStage } from './constants'
import { useTranslation } from '#i18n'
import { cn } from '@/utils/classnames'
import { resolveStageTheme } from './crm-theme'

type StageTagProps = {
  stage: string
  className?: string
}

export function StageTag({ stage, className }: StageTagProps) {
  const { t } = useTranslation('common')
  const stageKey = stage as MiniCrmStage
  const theme = resolveStageTheme(stage)
  const labelKey = {
    new: 'miniCrm.stageNew',
    qualified: 'miniCrm.stageQualified',
    won: 'miniCrm.stageWon',
    lost: 'miniCrm.stageLost',
  }[stageKey] as 'miniCrm.stageNew' | 'miniCrm.stageQualified' | 'miniCrm.stageWon' | 'miniCrm.stageLost' | undefined

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide',
        className,
      )}
      style={{
        backgroundColor: theme.bgColor,
        color: theme.color,
        border: `1px solid ${theme.borderColor}`,
      }}
    >
      {labelKey ? t(labelKey) : stage}
    </span>
  )
}
