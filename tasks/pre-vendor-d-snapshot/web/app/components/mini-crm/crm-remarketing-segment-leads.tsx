'use client'

import type { MiniCrmBusinessLine, MiniCrmLeadFormState } from './constants'
import type { MiniCrmLeadRow } from '@/service/tools'
import { useTranslation } from '#i18n'
import { RiArrowLeftLine } from '@remixicon/react'
import { Fragment, useCallback, useEffect, useState } from 'react'
import Loading from '@/app/components/base/loading'
import Pagination from '@/app/components/base/pagination'
import { toast } from '@/app/components/base/ui/toast'
import Link from '@/next/link'
import {
  bulkPatchMiniCrmLeads,
  exportMiniCrmRemarketingSegmentCsv,
  listMiniCrmRemarketingSegmentLeads,
  patchMiniCrmLead,
} from '@/service/tools'
import { useMembers } from '@/service/use-common'
import { leadRowToFormState, tagsInputToArray } from './constants'
import { CrmBulkToolbar } from './crm-bulk-toolbar'
import { CrmContactAvatar } from './crm-contact-avatar'
import { CrmLeadEditor } from './crm-lead-editor'
import { CrmLeadTags } from './crm-lead-tags'
import { CrmLeadTimeline } from './crm-lead-timeline'
import { CRM_BRAND } from './crm-theme'
import { StageTag } from './stage-tag'

const DEFAULT_PAGE_SIZE = 25

type CrmRemarketingSegmentLeadsProps = {
  businessLine: MiniCrmBusinessLine
  segmentKey: string
  segmentTitle: string
  channelTypeFilter: string
  resolveStageLabel: (stage: string) => string
  resolveChannelLabel: (channelType: string) => string
  onBack: () => void
  onLeadsChanged: () => void
}

function formatRelativeTime(iso: string | null | undefined, locale: string): string {
  if (!iso)
    return '-'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime()))
    return '-'
  return date.toLocaleString(locale)
}

export function CrmRemarketingSegmentLeads({
  businessLine,
  segmentKey,
  segmentTitle,
  channelTypeFilter,
  resolveStageLabel,
  resolveChannelLabel,
  onBack,
  onLeadsChanged,
}: CrmRemarketingSegmentLeadsProps) {
  const { t, i18n } = useTranslation('common')
  const { data: membersData } = useMembers()
  const [leadRows, setLeadRows] = useState<MiniCrmLeadRow[]>([])
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(0)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedConversationIds, setSelectedConversationIds] = useState<string[]>([])
  const [bulkStage, setBulkStage] = useState('')
  const [isBulkApplying, setIsBulkApplying] = useState(false)
  const [expandedConversationId, setExpandedConversationId] = useState<string | null>(null)
  const [inlineEditFormStateByConversationId, setInlineEditFormStateByConversationId] = useState<
    Record<string, MiniCrmLeadFormState>
  >({})
  const [savingConversationId, setSavingConversationId] = useState<string | null>(null)

  const resolveOwnerName = useCallback((ownerAccountId: string | null | undefined) => {
    if (!ownerAccountId)
      return t('miniCrm.ownerUnassigned')
    const account = membersData?.accounts?.find(item => item.id === ownerAccountId)
    return account?.name || t('miniCrm.ownerUnassigned')
  }, [membersData?.accounts, t])

  const loadLeads = useCallback(async (pageIndex: number) => {
    setIsLoading(true)
    try {
      const response = await listMiniCrmRemarketingSegmentLeads(segmentKey, {
        business_line: businessLine,
        channel_type: channelTypeFilter || undefined,
        offset: pageIndex * pageSize,
        limit: pageSize,
      })
      setLeadRows(response.data || [])
      setTotal(response.total ?? 0)
      setCurrentPage(pageIndex)
    }
    catch {
      toast.error(t('miniCrm.errorLoad'))
    }
    finally {
      setIsLoading(false)
    }
  }, [businessLine, channelTypeFilter, pageSize, segmentKey, t])

  useEffect(() => {
    setSelectedConversationIds([])
    setExpandedConversationId(null)
    setCurrentPage(0)
  }, [segmentKey, channelTypeFilter])

  useEffect(() => {
    void loadLeads(currentPage)
  }, [loadLeads, currentPage])

  const toggleLeadSelection = useCallback((conversationId: string) => {
    setSelectedConversationIds((previous) => {
      if (previous.includes(conversationId))
        return previous.filter(id => id !== conversationId)
      return [...previous, conversationId]
    })
  }, [])

  const toggleSelectAllVisible = useCallback(() => {
    setSelectedConversationIds((previous) => {
      const visibleIds = leadRows.map(row => row.conversation_id)
      const allSelected = visibleIds.length > 0 && visibleIds.every(id => previous.includes(id))
      if (allSelected)
        return previous.filter(id => !visibleIds.includes(id))
      return Array.from(new Set([...previous, ...visibleIds]))
    })
  }, [leadRows])

  const applyBulkStage = async () => {
    if (!bulkStage || !selectedConversationIds.length)
      return
    setIsBulkApplying(true)
    try {
      await bulkPatchMiniCrmLeads({
        conversation_ids: selectedConversationIds,
        stage: bulkStage,
      }, { business_line: businessLine })
      toast.success(t('miniCrm.bulkSuccess'))
      setSelectedConversationIds([])
      setBulkStage('')
      await loadLeads(currentPage)
      onLeadsChanged()
    }
    catch {
      toast.error(t('miniCrm.errorSave'))
    }
    finally {
      setIsBulkApplying(false)
    }
  }

  const beginInlineEditForLeadRow = useCallback((leadRow: MiniCrmLeadRow) => {
    setExpandedConversationId((previous) => {
      if (previous === leadRow.conversation_id)
        return null
      return leadRow.conversation_id
    })
    setInlineEditFormStateByConversationId(previous => ({
      ...previous,
      [leadRow.conversation_id]: leadRowToFormState(leadRow),
    }))
  }, [])

  const persistInlineLeadEdits = async (conversationId: string) => {
    const pendingFormState = inlineEditFormStateByConversationId[conversationId]
    if (!pendingFormState)
      return
    setSavingConversationId(conversationId)
    try {
      const patchResponse = await patchMiniCrmLead(conversationId, {
        stage: pendingFormState.stage,
        notes: pendingFormState.notes,
        source_override: pendingFormState.source_override || null,
        owner_account_id: pendingFormState.owner_account_id,
        tags: tagsInputToArray(pendingFormState.tags_input),
        contact_phone: pendingFormState.contact_phone || null,
        contact_email: pendingFormState.contact_email || null,
      })
      const updated = patchResponse.data
      if (updated) {
        setLeadRows(previous => previous.map(row =>
          row.conversation_id === conversationId ? { ...row, ...updated } : row,
        ))
      }
      toast.success(t('miniCrm.saveSuccess'))
      setExpandedConversationId(null)
      onLeadsChanged()
    }
    catch {
      toast.error(t('miniCrm.errorSave'))
    }
    finally {
      setSavingConversationId(null)
    }
  }

  const exportSegmentCsv = async () => {
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
  }

  const selectedLeadRows = leadRows.filter(row => selectedConversationIds.includes(row.conversation_id))

  const exportSelectedCsv = () => {
    if (!selectedLeadRows.length)
      return
    const header = ['conversation_id', 'contact_name', 'phone', 'email', 'stage', 'tags', 'channel_type']
    const escape = (value: string) => `"${value.replace(/"/g, '""')}"`
    const lines = [header.join(',')]
    for (const row of selectedLeadRows) {
      lines.push([
        row.conversation_id,
        (row.participant_display_name || '').trim() || row.external_user_id,
        row.contact_phone || '',
        row.contact_email || '',
        row.stage,
        (row.tags || []).join('; '),
        row.channel_type,
      ].map(value => escape(String(value))).join(','))
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `mini-crm-segment-${segmentKey}-selected.csv`
    anchor.rel = 'noopener'
    anchor.click()
    URL.revokeObjectURL(url)
    toast.success(t('miniCrm.exportSuccess'))
  }

  return (
    <div className="space-y-4">
      <div
        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3"
        style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
      >
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            className="inline-flex size-9 shrink-0 items-center justify-center rounded-lg border"
            style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textSecondary, backgroundColor: CRM_BRAND.headerBg }}
            onClick={onBack}
            aria-label={t('miniCrm.segmentBackToList')}
          >
            <RiArrowLeftLine className="size-4" aria-hidden />
          </button>
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold" style={{ color: CRM_BRAND.textPrimary }}>
              {segmentTitle}
            </h2>
            <p className="text-xs" style={{ color: CRM_BRAND.textSecondary }}>
              {t('miniCrm.segmentLeadsCount', { count: total })}
            </p>
          </div>
        </div>
      </div>

      <CrmBulkToolbar
        selectedCount={selectedConversationIds.length}
        bulkStage={bulkStage}
        isApplying={isBulkApplying}
        resolveStageLabel={resolveStageLabel}
        onBulkStageChange={setBulkStage}
        onApplyBulkStage={() => void applyBulkStage()}
        onExportSelected={exportSelectedCsv}
        onExportAll={() => void exportSegmentCsv()}
        onClearSelection={() => setSelectedConversationIds([])}
      />

      {isLoading && !leadRows.length
        ? (
            <div className="flex min-h-[12rem] items-center justify-center rounded-lg border" style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}>
              <Loading type="area" />
            </div>
          )
        : !leadRows.length
          ? (
              <div
                className="rounded-lg border border-dashed px-6 py-14 text-center"
                style={{ borderColor: CRM_BRAND.borderStrong, backgroundColor: CRM_BRAND.surface }}
              >
                <p className="text-sm font-semibold" style={{ color: CRM_BRAND.textPrimary }}>{t('miniCrm.segmentEmptyLeads')}</p>
              </div>
            )
          : (
              <div
                className="overflow-hidden rounded-lg border"
                style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
              >
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[960px] border-collapse text-left text-sm">
                    <thead>
                      <tr style={{ backgroundColor: CRM_BRAND.headerBg }}>
                        <th className="w-10 border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border }}>
                          <input
                            type="checkbox"
                            checked={leadRows.length > 0 && leadRows.every(row => selectedConversationIds.includes(row.conversation_id))}
                            onChange={toggleSelectAllVisible}
                            aria-label={t('miniCrm.selectAll')}
                          />
                        </th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.colContact')}</th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.channel')}</th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.colStage')}</th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.colOwner')}</th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.colUpdated')}</th>
                        <th className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border }} />
                      </tr>
                    </thead>
                    <tbody>
                      {leadRows.map((leadRow) => {
                        const isExpanded = expandedConversationId === leadRow.conversation_id
                        const formState = inlineEditFormStateByConversationId[leadRow.conversation_id]
                        const contactName = (leadRow.participant_display_name || '').trim() || leadRow.external_user_id
                        return (
                          <Fragment key={leadRow.conversation_id}>
                            <tr
                              className="cursor-pointer"
                              style={{ backgroundColor: isExpanded ? CRM_BRAND.primaryMuted : undefined }}
                              onClick={() => beginInlineEditForLeadRow(leadRow)}
                            >
                              <td className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border }} onClick={e => e.stopPropagation()}>
                                <input
                                  type="checkbox"
                                  checked={selectedConversationIds.includes(leadRow.conversation_id)}
                                  onChange={() => toggleLeadSelection(leadRow.conversation_id)}
                                  aria-label={t('miniCrm.selectLead')}
                                />
                              </td>
                              <td className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border }}>
                                <div className="flex items-center gap-3">
                                  <CrmContactAvatar name={contactName} stage={leadRow.stage} size="sm" />
                                  <div className="min-w-0">
                                    <div className="font-medium" style={{ color: CRM_BRAND.textPrimary }}>{contactName}</div>
                                    <CrmLeadTags tags={leadRow.tags} />
                                  </div>
                                </div>
                              </td>
                              <td className="border px-3 py-2.5 text-sm" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textSecondary }}>
                                {(leadRow.channel_name || '').trim() || resolveChannelLabel(leadRow.channel_type)}
                              </td>
                              <td className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border }}>
                                <StageTag stage={leadRow.stage} />
                              </td>
                              <td className="border px-3 py-2.5 text-sm" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textSecondary }}>
                                {resolveOwnerName(leadRow.owner_account_id)}
                              </td>
                              <td className="border px-3 py-2.5 text-xs tabular-nums" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>
                                {formatRelativeTime(leadRow.last_message_at || leadRow.crm_updated_at, i18n.language)}
                              </td>
                              <td className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border }}>
                                <Link
                                  href={`/omnichannel?channel_id=${encodeURIComponent(leadRow.channel_id)}&conversation_id=${encodeURIComponent(leadRow.conversation_id)}`}
                                  className="text-xs font-semibold hover:underline"
                                  style={{ color: CRM_BRAND.primaryDark }}
                                  onClick={e => e.stopPropagation()}
                                >
                                  {t('miniCrm.openInbox')}
                                </Link>
                              </td>
                            </tr>
                            {isExpanded && formState && (
                              <tr style={{ backgroundColor: CRM_BRAND.primaryMuted }}>
                                <td colSpan={7} className="border px-4 py-4" style={{ borderColor: CRM_BRAND.border }} onClick={e => e.stopPropagation()}>
                                  <CrmLeadEditor
                                    formState={formState}
                                    isSaving={savingConversationId === leadRow.conversation_id}
                                    onChange={(next) => {
                                      setInlineEditFormStateByConversationId(previous => ({
                                        ...previous,
                                        [leadRow.conversation_id]: next,
                                      }))
                                    }}
                                    onSave={() => void persistInlineLeadEdits(leadRow.conversation_id)}
                                    onCancel={() => setExpandedConversationId(null)}
                                    resolveStageLabel={resolveStageLabel}
                                  />
                                  <div className="mt-4 border-t border-divider-subtle pt-4">
                                    <div className="mb-2 text-xs font-medium text-text-tertiary">{t('miniCrm.activityLogTitle')}</div>
                                    <CrmLeadTimeline conversationId={leadRow.conversation_id} />
                                  </div>
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

      {!isLoading && total > 0 && (
        <div
          className="overflow-hidden rounded-lg border"
          style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
        >
          <Pagination
            current={currentPage}
            onChange={setCurrentPage}
            total={total}
            limit={pageSize}
            onLimitChange={(limit) => {
              setCurrentPage(0)
              setPageSize(limit)
            }}
          />
        </div>
      )}
    </div>
  )
}
