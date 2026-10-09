'use client'

import type { MiniCrmFunnelAnalytics } from '@/service/tools'
import { useTranslation } from '#i18n'
import { RiArrowDownSLine } from '@remixicon/react'
import { useMemo } from 'react'
import { MINI_CRM_STAGES } from './constants'
import { CRM_BRAND, resolveStageTheme } from './crm-theme'
import { StageTag } from './stage-tag'

type CrmPipelineFunnelProps = {
  analytics: MiniCrmFunnelAnalytics
  resolveStageLabel: (stage: string) => string
}

export function CrmPipelineFunnel({ analytics, resolveStageLabel }: CrmPipelineFunnelProps) {
  const { t } = useTranslation('common')

  const steps = useMemo(() => {
    const countByStage = new Map(
      (analytics.funnel_steps || []).map(step => [step.stage, step.count]),
    )
    return MINI_CRM_STAGES.map(stage => ({
      stage,
      count: countByStage.get(stage) ?? 0,
      label: resolveStageLabel(stage),
      theme: resolveStageTheme(stage),
    }))
  }, [analytics.funnel_steps, resolveStageLabel])

  const maxCount = Math.max(...steps.map(step => step.count), 1)
  const total = steps.reduce((sum, step) => sum + step.count, 0)

  const conversionBadges: Array<{ afterStage: string, pct: number, label: string }> = [
    {
      afterStage: 'new',
      pct: analytics.conversion.new_to_qualified_pct,
      label: t('miniCrm.funnelNewToQualified'),
    },
    {
      afterStage: 'qualified',
      pct: analytics.conversion.qualified_to_won_pct,
      label: t('miniCrm.funnelQualifiedToWon'),
    },
  ]

  return (
    <div className="px-2 py-4">
      <div className="mb-5 flex items-center justify-between gap-3">
        <span className="text-xs font-medium" style={{ color: CRM_BRAND.textSecondary }}>
          {t('miniCrm.total', { count: total })}
        </span>
        <span
          className="rounded-md px-2 py-1 text-xs font-bold tabular-nums"
          style={{ backgroundColor: resolveStageTheme('won').bgColor, color: resolveStageTheme('won').color }}
        >
          {t('miniCrm.funnelWinRate')}
          :
          {' '}
          {analytics.conversion.overall_win_pct}
          %
        </span>
      </div>

      <div className="space-y-1">
        {steps.map((step, index) => {
          const widthPct = Math.max((step.count / maxCount) * 100, step.count > 0 ? 8 : 2)
          const sharePct = total > 0 ? Math.round((step.count / total) * 100) : 0
          const badge = conversionBadges.find(item => item.afterStage === step.stage)

          return (
            <div key={step.stage}>
              <div className="flex items-center gap-3 py-2">
                <div className="w-[108px] shrink-0">
                  <StageTag stage={step.stage} />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <span className="truncate text-xs font-medium" style={{ color: CRM_BRAND.textSecondary }}>
                      {step.label}
                    </span>
                    <span className="shrink-0 text-xs tabular-nums" style={{ color: CRM_BRAND.textMuted }}>
                      {sharePct}
                      %
                    </span>
                  </div>
                  <div
                    className="h-9 overflow-hidden rounded-lg"
                    style={{ backgroundColor: CRM_BRAND.headerBg }}
                  >
                    <div
                      className="flex h-full items-center rounded-lg px-3"
                      style={{
                        width: `${widthPct}%`,
                        minWidth: step.count > 0 ? '3.5rem' : '0.5rem',
                        backgroundColor: step.theme.chartColor,
                      }}
                    >
                      <span className="text-sm font-bold tabular-nums text-white">
                        {step.count}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="w-12 shrink-0 text-right">
                  <div className="text-lg font-bold tabular-nums" style={{ color: step.theme.color }}>
                    {step.count}
                  </div>
                </div>
              </div>

              {badge && index < steps.length - 1 && (
                <div className="flex items-center gap-2 py-1 pl-[120px]">
                  <RiArrowDownSLine className="size-4 shrink-0" style={{ color: CRM_BRAND.textMuted }} aria-hidden />
                  <span
                    className="rounded-full px-2.5 py-0.5 text-[11px] font-semibold tabular-nums"
                    style={{
                      backgroundColor: CRM_BRAND.primaryMuted,
                      color: CRM_BRAND.primaryDark,
                    }}
                  >
                    {badge.pct}
                    %
                  </span>
                  <span className="text-[11px]" style={{ color: CRM_BRAND.textMuted }}>
                    {badge.label}
                  </span>
                </div>
              )}

            </div>
          )
        })}
      </div>
    </div>
  )
}
