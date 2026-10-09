'use client'

import type { MiniCrmStageCounts } from '@/service/tools'
import { useTranslation } from '#i18n'
import { RiArrowRightSLine } from '@remixicon/react'
import { cn } from '@/utils/classnames'
import { MINI_CRM_STAGES } from './constants'
import { CRM_BRAND, resolveStageTheme } from './crm-theme'
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
    <div
      className="overflow-hidden rounded-lg border"
      style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
    >
      <div
        className="flex items-center justify-between border-b px-4 py-2"
        style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.headerBg }}
      >
        <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: CRM_BRAND.textMuted }}>
          {t('miniCrm.funnelPipelineTitle')}
        </span>
        <button
          type="button"
          className="rounded-md px-2.5 py-1 text-xs font-semibold tabular-nums transition-colors"
          style={{
            color: !selectedStage ? CRM_BRAND.primaryDark : CRM_BRAND.textSecondary,
            backgroundColor: !selectedStage ? CRM_BRAND.primaryMuted : 'transparent',
            boxShadow: !selectedStage ? `inset 0 0 0 1px ${CRM_BRAND.primary}` : undefined,
          }}
          onClick={() => onStageSelect('')}
        >
          {t('miniCrm.summaryAll')}
          {' '}
          <span className="font-bold">{total}</span>
        </button>
      </div>

      <div className="grid grid-cols-2 sm:flex sm:flex-wrap sm:items-stretch">
        {MINI_CRM_STAGES.map((stage, index) => {
          const theme = resolveStageTheme(stage)
          const count = stageCounts?.[stage as keyof MiniCrmStageCounts] ?? 0
          const isActive = selectedStage === stage
          return (
            <div
              key={stage}
              className="flex min-w-0 flex-1 items-center sm:border-r sm:last:border-r-0"
              style={{ borderColor: CRM_BRAND.border }}
            >
              {index > 0 && (
                <RiArrowRightSLine
                  className="mx-0.5 hidden size-4 shrink-0 lg:block"
                  style={{ color: CRM_BRAND.textMuted }}
                  aria-hidden
                />
              )}
              <button
                type="button"
                className={cn(
                  'flex min-w-0 flex-1 flex-col px-4 py-3 text-left transition-colors hover:bg-[#F9FAFB]',
                  isActive && 'bg-[#F9FAFB]',
                )}
                style={isActive ? { boxShadow: `inset 0 -2px 0 ${theme.color}` } : undefined}
                onClick={() => onStageSelect(isActive ? '' : stage)}
              >
                <StageTag stage={stage} />
                <div
                  className="mt-2 text-2xl font-semibold tabular-nums tracking-tight"
                  style={{ color: isActive ? theme.color : CRM_BRAND.textPrimary }}
                >
                  {count}
                </div>
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
