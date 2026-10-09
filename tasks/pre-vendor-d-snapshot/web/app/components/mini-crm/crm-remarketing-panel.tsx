'use client'

import type { MiniCrmBusinessLine } from './constants'
import type { MiniCrmRemarketingSegment } from '@/service/tools'
import { useTranslation } from '#i18n'
import {
  RiCheckboxCircleLine,
  RiDownloadLine,
  RiRefreshLine,
  RiTimeLine,
  RiUserAddLine,
  RiVipCrownLine,
} from '@remixicon/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Loading from '@/app/components/base/loading'
import { toast } from '@/app/components/base/ui/toast'
import { usePathname, useRouter, useSearchParams } from '@/next/navigation'
import { exportMiniCrmRemarketingSegmentCsv, listMiniCrmRemarketingSegments } from '@/service/tools'
import { CRM_BRAND } from './crm-theme'
import { CrmRemarketingSegmentLeads } from './crm-remarketing-segment-leads'

type CrmRemarketingPanelProps = {
  businessLine: MiniCrmBusinessLine
  channelTypeFilter: string
  resolveStageLabel: (stage: string) => string
  resolveChannelLabel: (channelType: string) => string
}

const SEGMENT_TITLE_KEYS: Record<string, string> = {
  stale_qualified: 'miniCrm.segmentStaleQualified',
  lost_reengage: 'miniCrm.segmentLostReengage',
  new_unassigned: 'miniCrm.segmentNewUnassigned',
  tag_vip: 'miniCrm.segmentTagVip',
  won_followup: 'miniCrm.segmentWonFollowup',
}

const SEGMENT_DESC_KEYS: Record<string, string> = {
  stale_qualified: 'miniCrm.segmentStaleQualifiedDesc',
  lost_reengage: 'miniCrm.segmentLostReengageDesc',
  new_unassigned: 'miniCrm.segmentNewUnassignedDesc',
  tag_vip: 'miniCrm.segmentTagVipDesc',
  won_followup: 'miniCrm.segmentWonFollowupDesc',
}

const SEGMENT_THEME: Record<string, { icon: typeof RiTimeLine, color: string, bg: string }> = {
  stale_qualified: { icon: RiTimeLine, color: '#D97706', bg: '#FEF3C7' },
  lost_reengage: { icon: RiRefreshLine, color: '#E11D48', bg: '#FFE4E6' },
  new_unassigned: { icon: RiUserAddLine, color: '#2563EB', bg: '#DBEAFE' },
  tag_vip: { icon: RiVipCrownLine, color: '#7C3AED', bg: '#EDE9FE' },
  won_followup: { icon: RiCheckboxCircleLine, color: '#059669', bg: '#D1FAE5' },
}

const VALID_SEGMENT_KEYS = new Set(Object.keys(SEGMENT_TITLE_KEYS))

export function CrmRemarketingPanel({
  businessLine,
  channelTypeFilter,
  resolveStageLabel,
  resolveChannelLabel,
}: CrmRemarketingPanelProps) {
  const { t } = useTranslation('common')
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const rawSegment = searchParams.get('segment') ?? ''
  const selectedSegmentKey = VALID_SEGMENT_KEYS.has(rawSegment) ? rawSegment : ''

  const [segments, setSegments] = useState<MiniCrmRemarketingSegment[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [exportingKey, setExportingKey] = useState<string | null>(null)

  const loadSegments = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await listMiniCrmRemarketingSegments({
        business_line: businessLine,
        channel_type: channelTypeFilter || undefined,
      })
      setSegments(response.data || [])
    }
    catch {
      toast.error(t('miniCrm.errorLoad'))
    }
    finally {
      setIsLoading(false)
    }
  }, [businessLine, channelTypeFilter, t])

  useEffect(() => {
    void loadSegments()
  }, [loadSegments])

  const totalSegmentLeads = useMemo(
    () => segments.reduce((sum, segment) => sum + (segment.lead_count ?? 0), 0),
    [segments],
  )

  const setSelectedSegment = (segmentKey: string) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('segment', segmentKey)
    router.replace(`${pathname}?${params.toString()}`)
  }

  const clearSelectedSegment = () => {
    const params = new URLSearchParams(searchParams.toString())
    params.delete('segment')
    const query = params.toString()
    router.replace(query ? `${pathname}?${query}` : pathname)
  }

  const exportSegment = async (segmentKey: string) => {
    setExportingKey(segmentKey)
    try {
      const csv = await exportMiniCrmRemarketingSegmentCsv(segmentKey, {
        business_line: businessLine,
        channel_type: channelTypeFilter || undefined,
      })
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `mini-crm-segment-${segmentKey}.csv`
      anchor.rel = 'noopener'
      anchor.click()
      URL.revokeObjectURL(url)
      toast.success(t('miniCrm.exportSuccess'))
    }
    catch {
      toast.error(t('miniCrm.exportError'))
    }
    finally {
      setExportingKey(null)
    }
  }

  const resolveSegmentTitle = (segmentKey: string) => {
    const titleKey = SEGMENT_TITLE_KEYS[segmentKey]
    return titleKey ? t(titleKey as 'miniCrm.segmentStaleQualified') : segmentKey
  }

  if (selectedSegmentKey) {
    return (
      <CrmRemarketingSegmentLeads
        businessLine={businessLine}
        segmentKey={selectedSegmentKey}
        segmentTitle={resolveSegmentTitle(selectedSegmentKey)}
        channelTypeFilter={channelTypeFilter}
        resolveStageLabel={resolveStageLabel}
        resolveChannelLabel={resolveChannelLabel}
        onBack={clearSelectedSegment}
        onLeadsChanged={() => void loadSegments()}
      />
    )
  }

  if (isLoading && !segments.length) {
    return (
      <div className="flex min-h-[12rem] items-center justify-center rounded-lg border" style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}>
        <Loading type="area" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div
        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3"
        style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
      >
        <p className="text-sm" style={{ color: CRM_BRAND.textSecondary }}>
          {t('miniCrm.remarketingOverview', { count: totalSegmentLeads })}
        </p>
        <Button variant="secondary" size="small" onClick={() => void loadSegments()}>
          <RiRefreshLine className="mr-1 size-3.5" aria-hidden />
          {t('miniCrm.remarketingRefresh')}
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {segments.map((segment) => {
          const titleKey = SEGMENT_TITLE_KEYS[segment.key]
          const descKey = SEGMENT_DESC_KEYS[segment.key]
          const theme = SEGMENT_THEME[segment.key] ?? SEGMENT_THEME.new_unassigned
          const Icon = theme.icon
          return (
            <div
              key={segment.key}
              className="flex flex-col overflow-hidden rounded-lg border"
              style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
            >
              <div className="flex items-start gap-3 p-4">
                <div
                  className="flex size-11 shrink-0 items-center justify-center rounded-xl"
                  style={{ backgroundColor: theme.bg, color: theme.color }}
                >
                  <Icon className="size-5" aria-hidden />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-sm font-semibold" style={{ color: CRM_BRAND.textPrimary }}>
                      {titleKey ? t(titleKey as 'miniCrm.segmentStaleQualified') : segment.key}
                    </h3>
                    <div
                      className="shrink-0 rounded-lg px-2.5 py-1 text-lg font-bold tabular-nums"
                      style={{ backgroundColor: theme.bg, color: theme.color }}
                    >
                      {segment.lead_count ?? 0}
                    </div>
                  </div>
                  <p className="mt-1.5 text-xs leading-relaxed" style={{ color: CRM_BRAND.textSecondary }}>
                    {descKey ? t(descKey as 'miniCrm.segmentStaleQualifiedDesc') : ''}
                  </p>
                </div>
              </div>
              <div
                className="mt-auto flex flex-wrap gap-2 border-t px-4 py-3"
                style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.headerBg }}
              >
                <Button
                  variant="secondary"
                  size="small"
                  disabled={(segment.lead_count ?? 0) === 0}
                  onClick={() => setSelectedSegment(segment.key)}
                >
                  {t('miniCrm.segmentViewLeads')}
                </Button>
                <Button
                  variant="primary"
                  size="small"
                  loading={exportingKey === segment.key}
                  disabled={(segment.lead_count ?? 0) === 0}
                  onClick={() => void exportSegment(segment.key)}
                >
                  <RiDownloadLine className="mr-1 size-3.5" aria-hidden />
                  {t('miniCrm.segmentExport')}
                </Button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
