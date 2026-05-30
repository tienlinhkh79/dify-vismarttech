'use client'

import type { ReactNode } from 'react'
import type { MiniCrmFunnelAnalytics } from '@/service/tools'
import { useTranslation } from '#i18n'
import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import Loading from '@/app/components/base/loading'
import { SegmentedControl } from '@/app/components/base/segmented-control'

const STAGE_COLORS: Record<string, string> = {
  new: '#60A5FA',
  qualified: '#FBBF24',
  won: '#34D399',
  lost: '#F87171',
}

type CrmFunnelDashboardProps = {
  analytics: MiniCrmFunnelAnalytics | null
  isLoading: boolean
  periodDays: number
  onPeriodDaysChange: (days: number) => void
  resolveStageLabel: (stage: string) => string
  resolveChannelLabel: (channelType: string) => string
}

export function CrmFunnelDashboard({
  analytics,
  isLoading,
  periodDays,
  onPeriodDaysChange,
  resolveStageLabel,
  resolveChannelLabel,
}: CrmFunnelDashboardProps) {
  const { t } = useTranslation('common')

  const periodOptions = useMemo(() => ([
    { value: 7, text: t('miniCrm.analyticsPeriod7d') },
    { value: 30, text: t('miniCrm.analyticsPeriod30d') },
    { value: 90, text: t('miniCrm.analyticsPeriod90d') },
  ]), [t])

  const stagePieOptions = useMemo(() => {
    if (!analytics)
      return null
    const data = (analytics.funnel_steps || []).map(step => ({
      name: resolveStageLabel(step.stage),
      value: step.count,
      itemStyle: { color: STAGE_COLORS[step.stage] || '#94A3B8' },
    }))
    return {
      tooltip: { trigger: 'item' as const },
      legend: { bottom: 0, textStyle: { color: '#676F83' } },
      series: [{
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '44%'],
        data,
        label: { formatter: '{b}\n{c}' },
      }],
    }
  }, [analytics, resolveStageLabel])

  const funnelOptions = useMemo(() => {
    if (!analytics)
      return null
    const steps = analytics.funnel_steps || []
    return {
      tooltip: { trigger: 'item' as const, formatter: '{b}: {c}' },
      series: [{
        type: 'funnel',
        left: '8%',
        top: 16,
        bottom: 16,
        width: '84%',
        min: 0,
        max: Math.max(...steps.map(step => step.count), 1),
        sort: 'descending',
        gap: 4,
        label: { show: true, position: 'inside' as const },
        data: steps.map(step => ({
          name: resolveStageLabel(step.stage),
          value: step.count,
          itemStyle: { color: STAGE_COLORS[step.stage] || '#94A3B8' },
        })),
      }],
    }
  }, [analytics, resolveStageLabel])

  const trendOptions = useMemo(() => {
    if (!analytics)
      return null
    const points = analytics.daily_pipeline || []
    return {
      tooltip: { trigger: 'axis' as const },
      legend: { top: 0, textStyle: { color: '#676F83' } },
      grid: { left: 40, right: 16, top: 36, bottom: 28 },
      xAxis: {
        type: 'category' as const,
        data: points.map(point => point.date.slice(5)),
        axisLabel: { color: '#676F83' },
      },
      yAxis: {
        type: 'value' as const,
        minInterval: 1,
        axisLabel: { color: '#676F83' },
      },
      series: [
        {
          name: t('miniCrm.stageQualified'),
          type: 'line',
          smooth: true,
          data: points.map(point => point.qualified),
          itemStyle: { color: STAGE_COLORS.qualified },
        },
        {
          name: t('miniCrm.stageWon'),
          type: 'line',
          smooth: true,
          data: points.map(point => point.won),
          itemStyle: { color: STAGE_COLORS.won },
        },
        {
          name: t('miniCrm.stageLost'),
          type: 'line',
          smooth: true,
          data: points.map(point => point.lost),
          itemStyle: { color: STAGE_COLORS.lost },
        },
      ],
    }
  }, [analytics, t])

  const channelOptions = useMemo(() => {
    if (!analytics)
      return null
    const items = analytics.channel_breakdown || []
    return {
      tooltip: { trigger: 'axis' as const },
      grid: { left: 40, right: 16, top: 16, bottom: 48 },
      xAxis: {
        type: 'category' as const,
        data: items.map(item => resolveChannelLabel(item.channel_type)),
        axisLabel: { color: '#676F83', rotate: items.length > 4 ? 24 : 0 },
      },
      yAxis: {
        type: 'value' as const,
        minInterval: 1,
        axisLabel: { color: '#676F83' },
      },
      series: [{
        type: 'bar',
        data: items.map(item => item.count),
        itemStyle: { color: '#528BFF', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 40,
      }],
    }
  }, [analytics, resolveChannelLabel])

  if (isLoading && !analytics) {
    return (
      <div className="flex min-h-[16rem] items-center justify-center">
        <Loading type="area" />
      </div>
    )
  }

  if (!analytics)
    return null

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-text-secondary">
          {t('miniCrm.funnelRecentPeriod', { days: analytics.period_days })}
        </div>
        <SegmentedControl
          size="small"
          value={periodDays}
          onChange={onPeriodDaysChange}
          options={periodOptions}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: t('miniCrm.funnelWinRate'), value: `${analytics.conversion.overall_win_pct}%` },
          { label: t('miniCrm.funnelNewToQualified'), value: `${analytics.conversion.new_to_qualified_pct}%` },
          { label: t('miniCrm.funnelQualifiedToWon'), value: `${analytics.conversion.qualified_to_won_pct}%` },
          {
            label: t('miniCrm.funnelRecentWonLostLabel'),
            value: t('miniCrm.funnelRecentWonLost', { won: analytics.recent_won, lost: analytics.recent_lost }),
          },
        ].map(metric => (
          <div
            key={metric.label}
            className="rounded-xl bg-components-chart-bg px-4 py-3 shadow-xs ring-1 ring-divider-subtle"
          >
            <div className="text-xs text-text-tertiary">{metric.label}</div>
            <div className="mt-1 text-xl font-semibold text-text-primary tabular-nums">{metric.value}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard title={t('miniCrm.chartStageDistribution')}>
          {stagePieOptions && <ReactECharts option={stagePieOptions} style={{ height: 280 }} />}
        </ChartCard>
        <ChartCard title={t('miniCrm.funnelPipelineTitle')}>
          {funnelOptions && <ReactECharts option={funnelOptions} style={{ height: 280 }} />}
        </ChartCard>
        <ChartCard title={t('miniCrm.chartPipelineTrend')} className="xl:col-span-2">
          {trendOptions && <ReactECharts option={trendOptions} style={{ height: 300 }} />}
        </ChartCard>
        <ChartCard title={t('miniCrm.chartChannelBreakdown')} className="xl:col-span-2">
          {channelOptions && <ReactECharts option={channelOptions} style={{ height: 280 }} />}
        </ChartCard>
      </div>
    </div>
  )
}

function ChartCard({
  title,
  children,
  className,
}: {
  title: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`rounded-xl bg-components-chart-bg px-4 py-4 shadow-xs ring-1 ring-divider-subtle ${className ?? ''}`}>
      <h3 className="mb-3 text-sm font-semibold text-text-primary">{title}</h3>
      {children}
    </div>
  )
}
