'use client'

import type { MiniCrmRemarketingSegment } from '@/service/tools'
import { useTranslation } from '#i18n'
import { useCallback, useEffect, useState } from 'react'
import Button from '@/app/components/base/button'
import Loading from '@/app/components/base/loading'
import { toast } from '@/app/components/base/ui/toast'
import Link from '@/next/link'
import { exportMiniCrmRemarketingSegmentCsv, listMiniCrmRemarketingSegments } from '@/service/tools'

type CrmRemarketingPanelProps = {
  channelTypeFilter: string
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

export function CrmRemarketingPanel({ channelTypeFilter }: CrmRemarketingPanelProps) {
  const { t } = useTranslation('common')
  const [segments, setSegments] = useState<MiniCrmRemarketingSegment[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [exportingKey, setExportingKey] = useState<string | null>(null)

  const loadSegments = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await listMiniCrmRemarketingSegments({
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
  }, [channelTypeFilter, t])

  useEffect(() => {
    void loadSegments()
  }, [loadSegments])

  const exportSegment = async (segmentKey: string) => {
    setExportingKey(segmentKey)
    try {
      const csv = await exportMiniCrmRemarketingSegmentCsv(segmentKey, {
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

  if (isLoading && !segments.length) {
    return (
      <div className="flex min-h-[12rem] items-center justify-center">
        <Loading type="area" />
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {segments.map((segment) => {
        const titleKey = SEGMENT_TITLE_KEYS[segment.key]
        const descKey = SEGMENT_DESC_KEYS[segment.key]
        return (
          <div
            key={segment.key}
            className="flex flex-col rounded-xl bg-components-chart-bg p-4 shadow-xs ring-1 ring-divider-subtle"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-text-primary">
                  {titleKey ? t(titleKey as 'miniCrm.segmentStaleQualified') : segment.key}
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-text-tertiary">
                  {descKey ? t(descKey as 'miniCrm.segmentStaleQualifiedDesc') : ''}
                </p>
              </div>
              <div className="text-lg font-semibold text-text-accent tabular-nums">
                {segment.lead_count ?? 0}
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link
                href="/mini-crm?tab=remarketing"
                className="inline-flex"
              >
                <Button variant="secondary" size="small">
                  {t('miniCrm.segmentViewLeads')}
                </Button>
              </Link>
              <Button
                variant="primary"
                size="small"
                loading={exportingKey === segment.key}
                onClick={() => void exportSegment(segment.key)}
              >
                {t('miniCrm.segmentExport')}
              </Button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
