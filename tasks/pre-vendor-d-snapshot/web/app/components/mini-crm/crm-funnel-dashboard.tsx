'use client'

import type { ReactNode } from 'react'
import type { MiniCrmFunnelAnalytics } from '@/service/tools'
import { useTranslation } from '#i18n'
import { RiArrowRightLine, RiBarChartGroupedLine, RiPieChartLine, RiTrophyLine } from '@remixicon/react'
import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import Loading from '@/app/components/base/loading'
import { cn } from '@/utils/classnames'
import { CrmPipelineFunnel } from './crm-pipeline-funnel'
import { CRM_BRAND, CRM_CHART_AXIS, resolveStageTheme } from './crm-theme'

type CrmFunnelDashboardProps = {
  analytics: MiniCrmFunnelAnalytics | null
  isLoading: boolean
  periodDays: number
  onPeriodDaysChange: (days: number) => void
  resolveStageLabel: (stage: string) => string
  resolveChannelLabel: (channelType: string) => string
}

const METRIC_ICONS = [RiTrophyLine, RiArrowRightLine, RiArrowRightLine, RiBarChartGroupedLine]

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
      itemStyle: { color: resolveStageTheme(step.stage).chartColor },
    }))
    return {
      animationDuration: 800,
      animationEasing: 'cubicOut' as const,
      tooltip: {
        trigger: 'item' as const,
        borderWidth: 0,
        backgroundColor: CRM_CHART_AXIS.tooltipBg,
        textStyle: { color: '#F9FAFB', fontSize: 12 },
        formatter: '{b}: <b>{c}</b> ({d}%)',
      },
      legend: {
        bottom: 0,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: CRM_CHART_AXIS.label, fontSize: 12 },
      },
      series: [{
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '42%'],
        padAngle: 3,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        data,
        label: { show: false },
        emphasis: {
          scale: true,
          scaleSize: 6,
          label: { show: true, fontSize: 13, fontWeight: 600 },
        },
      }],
    }
  }, [analytics, resolveStageLabel])

  const trendOptions = useMemo(() => {
    if (!analytics)
      return null
    const points = analytics.daily_pipeline || []
    const buildSeries = (stage: 'qualified' | 'won' | 'lost', label: string) => {
      const theme = resolveStageTheme(stage)
      return {
        name: label,
        type: 'line' as const,
        smooth: true,
        showSymbol: points.length <= 14,
        symbolSize: 6,
        data: points.map(point => point[stage]),
        lineStyle: { color: theme.chartColor, width: 2.5 },
        itemStyle: { color: theme.chartColor },
      }
    }
    return {
      animationDuration: 1000,
      tooltip: {
        trigger: 'axis' as const,
        borderWidth: 0,
        backgroundColor: CRM_CHART_AXIS.tooltipBg,
        textStyle: { color: '#F9FAFB', fontSize: 12 },
      },
      legend: {
        top: 0,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: CRM_CHART_AXIS.label, fontSize: 12 },
      },
      grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
      xAxis: {
        type: 'category' as const,
        data: points.map(point => point.date.slice(5)),
        boundaryGap: false,
        axisLabel: { color: CRM_CHART_AXIS.label, fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value' as const,
        minInterval: 1,
        axisLabel: { color: CRM_CHART_AXIS.label, fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: CRM_CHART_AXIS.splitLine, type: 'dashed' as const } },
      },
      series: [
        buildSeries('qualified', t('miniCrm.stageQualified')),
        buildSeries('won', t('miniCrm.stageWon')),
        buildSeries('lost', t('miniCrm.stageLost')),
      ],
    }
  }, [analytics, t])

  const channelOptions = useMemo(() => {
    if (!analytics)
      return null
    const items = analytics.channel_breakdown || []
    return {
      animationDuration: 800,
      animationEasing: 'elasticOut' as const,
      tooltip: {
        trigger: 'axis' as const,
        borderWidth: 0,
        backgroundColor: CRM_CHART_AXIS.tooltipBg,
        textStyle: { color: '#F9FAFB', fontSize: 12 },
        axisPointer: { type: 'shadow' as const },
      },
      grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
      xAxis: {
        type: 'category' as const,
        data: items.map(item => resolveChannelLabel(item.channel_type)),
        axisLabel: {
          color: CRM_CHART_AXIS.label,
          fontSize: 11,
          rotate: items.length > 4 ? 20 : 0,
          interval: 0,
        },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value' as const,
        minInterval: 1,
        axisLabel: { color: CRM_CHART_AXIS.label, fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: CRM_CHART_AXIS.splitLine, type: 'dashed' as const } },
      },
      series: [{
        type: 'bar',
        data: items.map(item => item.count),
        barMaxWidth: 48,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: CRM_BRAND.primary,
        },
        emphasis: {
          itemStyle: {
            color: CRM_BRAND.primaryDark,
          },
        },
      }],
    }
  }, [analytics, resolveChannelLabel])

  if (isLoading && !analytics) {
    return (
      <div className="flex min-h-[16rem] items-center justify-center rounded-2xl border border-divider-subtle bg-background-default">
        <Loading type="area" />
      </div>
    )
  }

  if (!analytics)
    return null

  const metrics = [
    {
      label: t('miniCrm.funnelWinRate'),
      value: `${analytics.conversion.overall_win_pct}%`,
      accent: resolveStageTheme('won').color,
      iconBg: resolveStageTheme('won').bgColor,
    },
    {
      label: t('miniCrm.funnelNewToQualified'),
      value: `${analytics.conversion.new_to_qualified_pct}%`,
      accent: resolveStageTheme('new').color,
      iconBg: resolveStageTheme('new').bgColor,
    },
    {
      label: t('miniCrm.funnelQualifiedToWon'),
      value: `${analytics.conversion.qualified_to_won_pct}%`,
      accent: resolveStageTheme('qualified').color,
      iconBg: resolveStageTheme('qualified').bgColor,
    },
    {
      label: t('miniCrm.funnelRecentWonLostLabel'),
      value: t('miniCrm.funnelRecentWonLost', { won: analytics.recent_won, lost: analytics.recent_lost }),
      accent: resolveStageTheme('lost').color,
      iconBg: resolveStageTheme('lost').bgColor,
    },
  ]

  return (
    <div className="space-y-5">
      <div
        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3"
        style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
      >
        <div className="flex items-center gap-2">
          <div
            className="flex size-8 items-center justify-center rounded-lg"
            style={{ backgroundColor: CRM_BRAND.primaryMuted, color: CRM_BRAND.primary }}
          >
            <RiPieChartLine className="size-4" aria-hidden />
          </div>
          <span className="text-sm font-medium" style={{ color: CRM_BRAND.textSecondary }}>
            {t('miniCrm.funnelRecentPeriod', { days: analytics.period_days })}
          </span>
        </div>
        <div
          className="inline-flex rounded-lg border p-0.5"
          style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.headerBg }}
        >
          {periodOptions.map(opt => (
            <button
              key={opt.value}
              type="button"
              className={cn('rounded-md px-3 py-1 text-xs font-semibold transition-all')}
              style={{
                backgroundColor: periodDays === opt.value ? CRM_BRAND.surface : 'transparent',
                color: periodDays === opt.value ? CRM_BRAND.primaryDark : CRM_BRAND.textMuted,
                boxShadow: periodDays === opt.value ? `inset 0 0 0 1px ${CRM_BRAND.primary}` : undefined,
              }}
              onClick={() => onPeriodDaysChange(opt.value)}
            >
              {opt.text}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric, index) => {
          const Icon = METRIC_ICONS[index]
          return (
            <div
              key={metric.label}
              className="group relative overflow-hidden rounded-lg border px-4 py-4 transition-shadow hover:shadow-md"
              style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
            >
              <div
                className="absolute inset-y-0 left-0 w-1 rounded-l-2xl"
                style={{ backgroundColor: metric.accent }}
              />
              <div className="flex items-start justify-between gap-2 pl-2">
                <div className="min-w-0">
                  <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: CRM_BRAND.textMuted }}>{metric.label}</div>
                  <div className="mt-1.5 text-2xl font-semibold tracking-tight tabular-nums" style={{ color: CRM_BRAND.textPrimary }}>
                    {metric.value}
                  </div>
                </div>
                <div
                  className="flex size-9 shrink-0 items-center justify-center rounded-xl"
                  style={{ backgroundColor: metric.iconBg, color: metric.accent }}
                >
                  <Icon className="size-4" aria-hidden />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard title={t('miniCrm.chartStageDistribution')}>
          {stagePieOptions && <ReactECharts option={stagePieOptions} style={{ height: 300 }} notMerge lazyUpdate />}
        </ChartCard>
        <ChartCard title={t('miniCrm.funnelPipelineTitle')}>
          <CrmPipelineFunnel analytics={analytics} resolveStageLabel={resolveStageLabel} />
        </ChartCard>
        <ChartCard title={t('miniCrm.chartPipelineTrend')} className="xl:col-span-2">
          {trendOptions && <ReactECharts option={trendOptions} style={{ height: 320 }} notMerge lazyUpdate />}
        </ChartCard>
        <ChartCard title={t('miniCrm.chartChannelBreakdown')} className="xl:col-span-2">
          {channelOptions && <ReactECharts option={channelOptions} style={{ height: 300 }} notMerge lazyUpdate />}
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
    <div
      className={`overflow-hidden rounded-lg border ${className ?? ''}`}
      style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
    >
      <div className="border-b px-5 py-3" style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.headerBg }}>
        <h3 className="text-[11px] font-bold uppercase tracking-wider" style={{ color: CRM_BRAND.textMuted }}>{title}</h3>
      </div>
      <div className="px-3 py-2">
        {children}
      </div>
    </div>
  )
}
