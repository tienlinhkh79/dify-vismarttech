'use client'

import type { MiniCrmStageCounts } from '@/service/tools'
import { useTranslation } from '#i18n'
import { cn } from '@/utils/classnames'
import { MINI_CRM_STAGES } from './constants'
import { StageTag } from './stage-tag'

type CrmSummaryBarProps = {
  total: number
  stageCounts?: MiniCrmStageCounts | null
  selectedStage: string
  onStageSelect: (stage: string) => void
}

export function CrmSummaryBar({
  total,
  stageCounts,
  selectedStage,
  onStageSelect,
}: CrmSummaryBarProps) {
  const { t } = useTranslation('common')

  return (
    <div className="mb-4 flex flex-wrap gap-2">
      <button
        type="button"
        className={cn(
          'rounded-lg border px-3 py-2 text-left transition-colors',
          !selectedStage
            ? 'border-components-panel-border bg-components-chart-bg shadow-xs'
            : 'border-transparent bg-background-default-subtle hover:bg-state-base-hover',
        )}
        onClick={() => onStageSelect('')}
      >
        <div className="text-xs text-text-tertiary">{t('miniCrm.summaryAll')}</div>
        <div className="text-lg font-semibold text-text-primary tabular-nums">{total}</div>
      </button>
      {MINI_CRM_STAGES.map((stage) => {
        const count = stageCounts?.[stage as keyof MiniCrmStageCounts] ?? 0
        const isActive = selectedStage === stage
        return (
          <button
            key={stage}
            type="button"
            className={cn(
              'rounded-lg border px-3 py-2 text-left transition-colors',
              isActive
                ? 'border-components-panel-border bg-components-chart-bg shadow-xs'
                : 'border-transparent bg-background-default-subtle hover:bg-state-base-hover',
            )}
            onClick={() => onStageSelect(isActive ? '' : stage)}
          >
            <StageTag stage={stage} />
            <div className="mt-1 text-lg font-semibold text-text-primary tabular-nums">{count}</div>
          </button>
        )
      })}
    </div>
  )
}
