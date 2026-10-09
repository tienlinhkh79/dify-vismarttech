'use client'

import type { MiniCrmBusinessLine, MiniCrmLeadFormState, MiniCrmMainTab, MiniCrmViewMode } from '@/app/components/mini-crm/constants'
import type { MiniCrmFunnelAnalytics, MiniCrmLeadRow, MiniCrmStageCounts } from '@/service/tools'
import { useTranslation } from '#i18n'
import { RiContactsBookLine, RiSearchLine } from '@remixicon/react'
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Loading from '@/app/components/base/loading'
import Pagination from '@/app/components/base/pagination'
import { SkeletonRectangle, SkeletonRow } from '@/app/components/base/skeleton'
import { toast } from '@/app/components/base/ui/toast'
import { leadRowToFormState, MINI_CRM_CHANNEL_TYPES, tagsInputToArray } from '@/app/components/mini-crm/constants'
import { CrmBulkToolbar } from '@/app/components/mini-crm/crm-bulk-toolbar'
import { CrmContactAvatar } from '@/app/components/mini-crm/crm-contact-avatar'
import { CrmFunnelDashboard } from '@/app/components/mini-crm/crm-funnel-dashboard'
import { CrmKanbanBoard } from '@/app/components/mini-crm/crm-kanban-board'
import { CrmLeadEditor } from '@/app/components/mini-crm/crm-lead-editor'
import { CrmLeadTags } from '@/app/components/mini-crm/crm-lead-tags'
import { CrmLeadTimeline } from '@/app/components/mini-crm/crm-lead-timeline'
import { CrmRemarketingPanel } from '@/app/components/mini-crm/crm-remarketing-panel'
import { CrmSummaryBar } from '@/app/components/mini-crm/crm-summary-bar'
import { CRM_BRAND } from '@/app/components/mini-crm/crm-theme'
import { CrmViewSwitcher } from '@/app/components/mini-crm/crm-view-switcher'
import { StageTag } from '@/app/components/mini-crm/stage-tag'
import Link from '@/next/link'
import { useSearchParams } from '@/next/navigation'
import {
  bulkPatchMiniCrmLeads,
  exportMiniCrmLeadsCsv,
  getMiniCrmFunnelAnalytics,
  listMiniCrmLeads,
  patchMiniCrmLead,
} from '@/service/tools'
import { useMembers } from '@/service/use-common'
import { cn } from '@/utils/classnames'

const DEFAULT_PAGE_SIZE = 25

type MiniCrmPageContentProps = {
  businessLine: MiniCrmBusinessLine
  mainTab: MiniCrmMainTab
}

function downloadCsvFile(csvContent: string, filename: string) {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.rel = 'noopener'
  anchor.click()
  URL.revokeObjectURL(url)
}

function buildSelectedLeadsCsv(rows: MiniCrmLeadRow[]): string {
  const header = [
    'conversation_id',
    'contact_name',
    'external_user_id',
    'phone',
    'email',
    'channel_type',
    'source',
    'stage',
    'tags',
    'notes',
  ]
  const escape = (value: string) => `"${value.replace(/"/g, '""')}"`
  const lines = [header.join(',')]
  for (const row of rows) {
    lines.push([
      row.conversation_id,
      (row.participant_display_name || '').trim() || row.external_user_id,
      row.external_user_id,
      row.contact_phone || '',
      row.contact_email || '',
      row.channel_type,
      row.source_display,
      row.stage,
      (row.tags || []).join('; '),
      row.notes || '',
    ].map(value => escape(String(value))).join(','))
  }
  return lines.join('\n')
}

function formatRelativeTime(iso: string | null | undefined, locale: string): string {
  if (!iso)
    return '-'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime()))
    return '-'
  return date.toLocaleString(locale)
}

function truncateText(text: string | null | undefined, maxLength: number): string {
  const value = (text || '').trim()
  if (!value)
    return ''
  if (value.length <= maxLength)
    return value
  return `${value.slice(0, maxLength)}…`
}

const MiniCrmPageContent = ({ businessLine, mainTab }: MiniCrmPageContentProps) => {
  const { t, i18n } = useTranslation('common')
  const searchParams = useSearchParams()
  const urlConversationId = searchParams.get('conversation_id') ?? ''
  const { data: membersData } = useMembers()
  const [funnelAnalytics, setFunnelAnalytics] = useState<MiniCrmFunnelAnalytics | null>(null)
  const [isFunnelLoading, setIsFunnelLoading] = useState(false)
  const [analyticsPeriodDays, setAnalyticsPeriodDays] = useState(30)

  const [crmLeadRows, setCrmLeadRows] = useState<MiniCrmLeadRow[]>([])
  const [totalLeadCount, setTotalLeadCount] = useState(0)
  const [stageCounts, setStageCounts] = useState<MiniCrmStageCounts | null>(null)
  const [selectedChannelTypeFilter, setSelectedChannelTypeFilter] = useState('')
  const [selectedPipelineStageFilter, setSelectedPipelineStageFilter] = useState('')
  const [appliedSearchQuery, setAppliedSearchQuery] = useState('')
  const [searchQueryInput, setSearchQueryInput] = useState('')
  const [isLeadListLoading, setIsLeadListLoading] = useState(false)
  const [expandedConversationId, setExpandedConversationId] = useState<string | null>(null)
  const [inlineEditFormStateByConversationId, setInlineEditFormStateByConversationId] = useState<
    Record<string, MiniCrmLeadFormState>
  >({})
  const [savingConversationId, setSavingConversationId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<MiniCrmViewMode>('table')
  const [selectedConversationIds, setSelectedConversationIds] = useState<string[]>([])
  const [bulkStage, setBulkStage] = useState('')
  const [isBulkApplying, setIsBulkApplying] = useState(false)
  const [currentPage, setCurrentPage] = useState(0)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const pendingDeepConversationIdRef = useRef<string | null>(null)
  const leadRowElementsRef = useRef<Record<string, HTMLElement | null>>({})

  const resetLeadListPagination = useCallback(() => {
    setSelectedConversationIds([])
    setCurrentPage(0)
  }, [])

  useEffect(() => {
    resetLeadListPagination()
  }, [businessLine, resetLeadListPagination])

  const resolveOwnerName = useCallback((ownerAccountId: string | null | undefined) => {
    if (!ownerAccountId)
      return t('miniCrm.ownerUnassigned')
    const account = membersData?.accounts?.find(item => item.id === ownerAccountId)
    return account?.name || t('miniCrm.ownerUnassigned')
  }, [membersData?.accounts, t])

  const loadLeads = useCallback(async (pageIndex: number) => {
    setIsLeadListLoading(true)
    try {
      const listResponse = await listMiniCrmLeads({
        business_line: businessLine,
        channel_type: selectedChannelTypeFilter || undefined,
        stage: selectedPipelineStageFilter || undefined,
        search_query: appliedSearchQuery || undefined,
        page: pageIndex + 1,
        page_size: pageSize,
      })
      setCrmLeadRows(listResponse.data || [])
      setTotalLeadCount(listResponse.total ?? 0)
      setStageCounts(listResponse.stage_counts ?? null)
      setCurrentPage(Math.max((listResponse.page ?? pageIndex + 1) - 1, 0))
    }
    catch {
      toast.error(t('miniCrm.errorLoad'))
    }
    finally {
      setIsLeadListLoading(false)
    }
  }, [businessLine, selectedChannelTypeFilter, selectedPipelineStageFilter, appliedSearchQuery, pageSize, t])

  useEffect(() => {
    void loadLeads(currentPage)
  }, [loadLeads, currentPage])

  const loadFunnelAnalytics = useCallback(async () => {
    setIsFunnelLoading(true)
    try {
      const response = await getMiniCrmFunnelAnalytics({
        business_line: businessLine,
        channel_type: selectedChannelTypeFilter || undefined,
        period_days: analyticsPeriodDays,
      })
      setFunnelAnalytics(response)
    }
    catch {
      toast.error(t('miniCrm.errorLoad'))
    }
    finally {
      setIsFunnelLoading(false)
    }
  }, [analyticsPeriodDays, businessLine, selectedChannelTypeFilter, t])

  useEffect(() => {
    if (mainTab === 'analytics')
      void loadFunnelAnalytics()
  }, [mainTab, loadFunnelAnalytics])

  useEffect(() => {
    const deepConversationId = urlConversationId.trim()
    if (!deepConversationId)
      return
    pendingDeepConversationIdRef.current = deepConversationId
  }, [urlConversationId])

  useEffect(() => {
    const pending = pendingDeepConversationIdRef.current
    if (!pending || isLeadListLoading)
      return
    const leadRow = crmLeadRows.find(row => row.conversation_id === pending)
    if (!leadRow)
      return
    pendingDeepConversationIdRef.current = null
    queueMicrotask(() => {
      setExpandedConversationId(leadRow.conversation_id)
      setInlineEditFormStateByConversationId(previous => ({
        ...previous,
        [leadRow.conversation_id]: leadRowToFormState(leadRow),
      }))
    })
    requestAnimationFrame(() => {
      leadRowElementsRef.current[leadRow.conversation_id]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }, [crmLeadRows, isLeadListLoading])

  const beginInlineEditForLeadRow = useCallback((leadRow: MiniCrmLeadRow) => {
    setExpandedConversationId((previous) => {
      if (previous === leadRow.conversation_id)
        return null
      return leadRow.conversation_id
    })
    setInlineEditFormStateByConversationId((previous: Record<string, MiniCrmLeadFormState>) => ({
      ...previous,
      [leadRow.conversation_id]: leadRowToFormState(leadRow),
    }))
  }, [])

  const persistInlineLeadEdits = useCallback(async (conversationId: string) => {
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
      const patchedLeadRow = patchResponse.data
      setCrmLeadRows((previousRows: MiniCrmLeadRow[]) =>
        previousRows.map((leadRow: MiniCrmLeadRow) =>
          leadRow.conversation_id === conversationId ? { ...leadRow, ...patchedLeadRow } : leadRow,
        ),
      )
      setExpandedConversationId(null)
      toast.success(t('miniCrm.saveSuccess'))
      void loadLeads(currentPage)
    }
    catch {
      toast.error(t('miniCrm.errorSave'))
    }
    finally {
      setSavingConversationId(null)
    }
  }, [currentPage, inlineEditFormStateByConversationId, loadLeads, t])

  const resolvePipelineStageLabel = useMemo(() => {
    const labelByStageValue: Record<string, string> = {
      new: t('miniCrm.stageNew'),
      qualified: t('miniCrm.stageQualified'),
      won: t('miniCrm.stageWon'),
      lost: t('miniCrm.stageLost'),
    }
    return (stageValue: string) => labelByStageValue[stageValue] || stageValue
  }, [t])

  const resolveOmnichannelTypeTitle = useMemo(() => {
    const labelByChannelType: Record<string, string> = {
      facebook_messenger: t('miniCrm.channelType.facebook_messenger'),
      instagram_dm: t('miniCrm.channelType.instagram_dm'),
      tiktok_messaging: t('miniCrm.channelType.tiktok_messaging'),
      zalo_oa: t('miniCrm.channelType.zalo_oa'),
      zalo_personal: t('miniCrm.channelType.zalo_personal'),
      website_widget: t('miniCrm.channelType.website_widget'),
    }
    return (channelTypeValue: string) => labelByChannelType[channelTypeValue] || channelTypeValue
  }, [t])

  const selectedLeadRows = useMemo(
    () => crmLeadRows.filter(row => selectedConversationIds.includes(row.conversation_id)),
    [crmLeadRows, selectedConversationIds],
  )

  const toggleLeadSelection = useCallback((conversationId: string) => {
    setSelectedConversationIds((previous) => {
      if (previous.includes(conversationId))
        return previous.filter(id => id !== conversationId)
      return [...previous, conversationId]
    })
  }, [])

  const toggleSelectAllVisible = useCallback(() => {
    setSelectedConversationIds((previous) => {
      const visibleIds = crmLeadRows.map(row => row.conversation_id)
      const allSelected = visibleIds.length > 0 && visibleIds.every(id => previous.includes(id))
      if (allSelected)
        return previous.filter(id => !visibleIds.includes(id))
      return Array.from(new Set([...previous, ...visibleIds]))
    })
  }, [crmLeadRows])

  const applyBulkStage = useCallback(async () => {
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
      void loadLeads(currentPage)
    }
    catch {
      toast.error(t('miniCrm.errorSave'))
    }
    finally {
      setIsBulkApplying(false)
    }
  }, [bulkStage, businessLine, currentPage, loadLeads, selectedConversationIds, t])

  const exportAllLeads = useCallback(async () => {
    try {
      const csv = await exportMiniCrmLeadsCsv({
        business_line: businessLine,
        channel_type: selectedChannelTypeFilter || undefined,
        stage: selectedPipelineStageFilter || undefined,
        search_query: appliedSearchQuery || undefined,
      })
      downloadCsvFile(csv, 'mini-crm-leads.csv')
      toast.success(t('miniCrm.exportSuccess'))
    }
    catch {
      toast.error(t('miniCrm.exportError'))
    }
  }, [appliedSearchQuery, businessLine, selectedChannelTypeFilter, selectedPipelineStageFilter, t])

  const exportSelectedLeads = useCallback(() => {
    if (!selectedLeadRows.length)
      return
    downloadCsvFile(buildSelectedLeadsCsv(selectedLeadRows), 'mini-crm-selected.csv')
    toast.success(t('miniCrm.exportSuccess'))
  }, [selectedLeadRows, t])

  const handleKanbanLeadUpdated = useCallback((updatedLeadRow: MiniCrmLeadRow) => {
    setCrmLeadRows(previousRows =>
      previousRows.map(row =>
        row.conversation_id === updatedLeadRow.conversation_id ? { ...row, ...updatedLeadRow } : row,
      ),
    )
    void loadLeads(currentPage)
  }, [currentPage, loadLeads])

  const isInitialLoading = isLeadListLoading && !crmLeadRows.length
  const isEmpty = !isLeadListLoading && crmLeadRows.length === 0

  const renderLeadCard = (leadRow: MiniCrmLeadRow) => {
    const isExpanded = expandedConversationId === leadRow.conversation_id
    const formState = inlineEditFormStateByConversationId[leadRow.conversation_id]
    const contactName = (leadRow.participant_display_name || '').trim() || leadRow.external_user_id

    return (
      <div
        key={leadRow.conversation_id}
        ref={(node) => {
          leadRowElementsRef.current[leadRow.conversation_id] = node
        }}
        className="overflow-hidden rounded-lg border transition-shadow hover:shadow-md"
        style={{
          borderColor: CRM_BRAND.border,
          backgroundColor: CRM_BRAND.surface,
          boxShadow: isExpanded ? `0 0 0 2px ${CRM_BRAND.primary}33` : undefined,
        }}
      >
        <button
          type="button"
          className="w-full p-4 text-left"
          onClick={() => beginInlineEditForLeadRow(leadRow)}
        >
          <div className="flex items-start gap-3">
            <CrmContactAvatar name={contactName} stage={leadRow.stage} size="sm" />
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate font-medium text-text-primary">{contactName}</div>
                  <div className="truncate text-xs text-text-tertiary">{leadRow.external_user_id}</div>
                </div>
                <StageTag stage={leadRow.stage} />
              </div>
            </div>
          </div>
          <div className="mt-3 space-y-1 text-xs text-text-secondary">
            <div>
              {resolveOmnichannelTypeTitle(leadRow.channel_type)}
              {' '}
              ·
              {' '}
              {leadRow.source_display}
            </div>
            <div>
              {t('miniCrm.colOwner')}
              :
              {' '}
              {resolveOwnerName(leadRow.owner_account_id)}
            </div>
            <CrmLeadTags tags={leadRow.tags} />
            <div className="text-text-quaternary tabular-nums">
              {t('miniCrm.colUpdated')}
              :
              {formatRelativeTime(leadRow.crm_updated_at, i18n.language)}
            </div>
          </div>
        </button>
        <div className="flex justify-end border-t border-divider-subtle px-4 py-2.5">
          <Link
            href={`/omnichannel?channel_id=${encodeURIComponent(leadRow.channel_id)}&conversation_id=${encodeURIComponent(leadRow.conversation_id)}`}
            className="text-xs font-medium text-text-accent hover:underline"
            onClick={e => e.stopPropagation()}
          >
            {t('miniCrm.openInbox')}
          </Link>
        </div>
        {isExpanded && formState && (
          <div className="border-t border-divider-subtle px-4 pb-4 pt-4">
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
              resolveStageLabel={resolvePipelineStageLabel}
            />
            <div className="mt-4 border-t border-divider-subtle pt-4">
              <div className="mb-2 text-xs font-medium text-text-tertiary">{t('miniCrm.activityLogTitle')}</div>
              <CrmLeadTimeline conversationId={leadRow.conversation_id} />
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden" style={{ backgroundColor: CRM_BRAND.workspace }}>
        <header
          className="shrink-0 border-b px-4 py-4 sm:px-6"
          style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-lg font-semibold tracking-tight" style={{ color: CRM_BRAND.textPrimary }}>
                {businessLine === 'nail' ? t('menus.miniCrmNails') : t('menus.miniCrmRestaurant')}
                {' · '}
                {mainTab === 'leads' && t('miniCrm.tabLeads')}
                {mainTab === 'analytics' && t('miniCrm.tabAnalytics')}
                {mainTab === 'remarketing' && t('miniCrm.tabRemarketing')}
              </h1>
              <p className="mt-0.5 text-xs" style={{ color: CRM_BRAND.textSecondary }}>
                {mainTab === 'remarketing'
                  ? t('miniCrm.remarketingSubtitle')
                  : t('miniCrm.pageSubtitle')}
              </p>
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-bold uppercase tracking-wider" style={{ color: CRM_BRAND.textMuted }}>
                {t('miniCrm.channel')}
              </label>
              <select
                className="h-9 min-w-[200px] rounded-md border px-3 text-sm"
                style={{
                  borderColor: CRM_BRAND.border,
                  backgroundColor: CRM_BRAND.surface,
                  color: CRM_BRAND.textPrimary,
                }}
                value={selectedChannelTypeFilter}
                onChange={(e) => {
                  resetLeadListPagination()
                  setSelectedChannelTypeFilter(e.target.value)
                }}
              >
                <option value="">{t('miniCrm.channelAll')}</option>
                {MINI_CRM_CHANNEL_TYPES.map(ct => (
                  <option key={ct} value={ct}>{resolveOmnichannelTypeTitle(ct)}</option>
                ))}
              </select>
            </div>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">

        {mainTab === 'analytics' && (
          <CrmFunnelDashboard
            analytics={funnelAnalytics}
            isLoading={isFunnelLoading}
            periodDays={analyticsPeriodDays}
            onPeriodDaysChange={setAnalyticsPeriodDays}
            resolveStageLabel={resolvePipelineStageLabel}
            resolveChannelLabel={resolveOmnichannelTypeTitle}
          />
        )}

        {mainTab === 'remarketing' && (
          <CrmRemarketingPanel
            businessLine={businessLine}
            channelTypeFilter={selectedChannelTypeFilter}
            resolveStageLabel={resolvePipelineStageLabel}
            resolveChannelLabel={resolveOmnichannelTypeTitle}
          />
        )}

        {mainTab === 'leads' && (
          <>
            <CrmSummaryBar
              total={totalLeadCount}
              stageCounts={stageCounts}
              selectedStage={selectedPipelineStageFilter}
              onStageSelect={(stage) => {
                resetLeadListPagination()
                setSelectedPipelineStageFilter(stage)
              }}
            />

            <div
              className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border px-3 py-2.5"
              style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
            >
              <CrmViewSwitcher
                value={viewMode}
                onChange={(mode) => {
                  resetLeadListPagination()
                  setViewMode(mode)
                }}
              />
              <div className="mx-1 hidden h-6 w-px sm:block" style={{ backgroundColor: CRM_BRAND.border }} />
              <div className="relative min-w-[200px] flex-1">
                <RiSearchLine
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2"
                  style={{ color: CRM_BRAND.textMuted }}
                  aria-hidden
                />
                <input
                  className="h-9 w-full rounded-md border pl-9 pr-3 text-sm outline-none focus:border-[#3ABDAF] focus:ring-2 focus:ring-[rgba(58,189,175,0.25)]"
                  style={{
                    borderColor: CRM_BRAND.border,
                    backgroundColor: CRM_BRAND.headerBg,
                    color: CRM_BRAND.textPrimary,
                  }}
                  value={searchQueryInput}
                  onChange={e => setSearchQueryInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      resetLeadListPagination()
                      setAppliedSearchQuery(searchQueryInput.trim())
                    }
                  }}
                  placeholder={t('miniCrm.filterSearchPlaceholder')}
                />
              </div>
              <button
                type="button"
                className="h-9 shrink-0 rounded-md px-4 text-sm font-semibold text-white transition-opacity hover:opacity-90"
                style={{ backgroundColor: CRM_BRAND.primary }}
                onClick={() => {
                  resetLeadListPagination()
                  setAppliedSearchQuery(searchQueryInput.trim())
                }}
              >
                {t('operation.search')}
              </button>
            </div>

            <CrmBulkToolbar
              selectedCount={selectedConversationIds.length}
              bulkStage={bulkStage}
              isApplying={isBulkApplying}
              resolveStageLabel={resolvePipelineStageLabel}
              onBulkStageChange={setBulkStage}
              onApplyBulkStage={() => void applyBulkStage()}
              onExportSelected={exportSelectedLeads}
              onExportAll={() => void exportAllLeads()}
              onClearSelection={() => setSelectedConversationIds([])}
            />

            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-medium text-text-tertiary">{t('miniCrm.total', { count: totalLeadCount })}</span>
            </div>

            {isInitialLoading && (
              <div className="space-y-2 rounded-xl border border-divider-regular bg-background-default p-4">
                {Array.from({ length: 5 }).map((_, index) => (
                  <SkeletonRow key={index}>
                    <SkeletonRectangle className="h-10 w-full" />
                  </SkeletonRow>
                ))}
              </div>
            )}

            {isEmpty && (
              <div
                className="rounded-lg border border-dashed px-6 py-16 text-center"
                style={{ borderColor: CRM_BRAND.borderStrong, backgroundColor: CRM_BRAND.surface }}
              >
                <div
                  className="mx-auto mb-4 flex size-14 items-center justify-center rounded-xl"
                  style={{ backgroundColor: CRM_BRAND.primaryMuted, color: CRM_BRAND.primary }}
                >
                  <RiContactsBookLine className="size-7" aria-hidden />
                </div>
                <p className="text-sm font-semibold" style={{ color: CRM_BRAND.textPrimary }}>{t('miniCrm.emptyLeads')}</p>
                <p className="mx-auto mt-1.5 max-w-sm text-xs" style={{ color: CRM_BRAND.textSecondary }}>{t('miniCrm.emptyLeadsHint')}</p>
              </div>
            )}

            {!isInitialLoading && !isEmpty && viewMode === 'kanban' && (
              <CrmKanbanBoard
                leadRows={crmLeadRows}
                isLoading={isLeadListLoading}
                resolveStageLabel={resolvePipelineStageLabel}
                resolveChannelLabel={resolveOmnichannelTypeTitle}
                onLeadUpdated={handleKanbanLeadUpdated}
              />
            )}

            {!isInitialLoading && !isEmpty && viewMode === 'table' && (
              <>
                <div className="space-y-3 md:hidden">
                  {crmLeadRows.map(renderLeadCard)}
                </div>

                <div
                  className="hidden overflow-hidden rounded-lg border md:block"
                  style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
                >
                  <div className="overflow-x-auto">
                  <table className="w-full min-w-[1100px] border-collapse text-left text-sm">
                    <thead>
                      <tr style={{ backgroundColor: CRM_BRAND.headerBg }}>
                        <th className="w-10 border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border }}>
                          <input
                            type="checkbox"
                            checked={crmLeadRows.length > 0 && crmLeadRows.every(row => selectedConversationIds.includes(row.conversation_id))}
                            onChange={toggleSelectAllVisible}
                            aria-label={t('miniCrm.selectAll')}
                          />
                        </th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.colContact')}</th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.channel')}</th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.colSource')}</th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.colStage')}</th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.colOwner')}</th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.colContactInfo')}</th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.tagsLabel')}</th>
                        <th className="border px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>{t('miniCrm.colUpdated')}</th>
                        <th className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border }} />
                      </tr>
                    </thead>
                    <tbody>
                      {crmLeadRows.map((leadRow) => {
                        const isExpanded = expandedConversationId === leadRow.conversation_id
                        const formState = inlineEditFormStateByConversationId[leadRow.conversation_id]
                        const contactName = (leadRow.participant_display_name || '').trim() || leadRow.external_user_id

                        return (
                          <Fragment key={leadRow.conversation_id}>
                            <tr
                              ref={(node) => {
                                leadRowElementsRef.current[leadRow.conversation_id] = node
                              }}
                              className="cursor-pointer transition-colors"
                              style={{
                                backgroundColor: isExpanded ? CRM_BRAND.primaryMuted : undefined,
                              }}
                              onMouseEnter={(e) => {
                                if (!isExpanded)
                                  e.currentTarget.style.backgroundColor = '#F9FAFB'
                              }}
                              onMouseLeave={(e) => {
                                if (!isExpanded)
                                  e.currentTarget.style.backgroundColor = ''
                              }}
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
                              <td className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textPrimary }}>
                                <div className="flex items-center gap-3">
                                  <CrmContactAvatar name={contactName} stage={leadRow.stage} size="sm" />
                                  <div className="min-w-0">
                                    <div className="font-medium">{contactName}</div>
                                    <div className="text-xs text-text-tertiary">{leadRow.external_user_id}</div>
                                    {leadRow.notes && (
                                      <div className="mt-1 line-clamp-1 text-xs text-text-quaternary">
                                        {truncateText(leadRow.notes, 80)}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </td>
                              <td className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textSecondary }}>
                                {(leadRow.channel_name || '').trim() || resolveOmnichannelTypeTitle(leadRow.channel_type)}
                              </td>
                              <td className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textSecondary }}>{leadRow.source_display}</td>
                              <td className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border }}>
                                <StageTag stage={leadRow.stage} />
                              </td>
                              <td className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textSecondary }}>{resolveOwnerName(leadRow.owner_account_id)}</td>
                              <td className="border px-3 py-2.5 text-xs" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textSecondary }}>
                                {leadRow.contact_phone && <div>{leadRow.contact_phone}</div>}
                                {leadRow.contact_email && <div className="truncate">{leadRow.contact_email}</div>}
                                {!leadRow.contact_phone && !leadRow.contact_email && '-'}
                              </td>
                              <td className="border px-3 py-2.5" style={{ borderColor: CRM_BRAND.border }}>
                                <CrmLeadTags tags={leadRow.tags} />
                              </td>
                              <td className="border px-3 py-2.5 text-xs tabular-nums" style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textMuted }}>
                                {formatRelativeTime(leadRow.crm_updated_at, i18n.language)}
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
                                <td colSpan={10} className="border px-4 py-4" style={{ borderColor: CRM_BRAND.border }} onClick={e => e.stopPropagation()}>
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
                                    resolveStageLabel={resolvePipelineStageLabel}
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
              </>
            )}

            {!isInitialLoading && !isEmpty && (
              <div
                className="mt-4 overflow-hidden rounded-lg border"
                style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.surface }}
              >
                <Pagination
                  current={currentPage}
                  onChange={setCurrentPage}
                  total={totalLeadCount}
                  limit={pageSize}
                  onLimitChange={(limit) => {
                    resetLeadListPagination()
                    setPageSize(limit)
                  }}
                />
              </div>
            )}
          </>
        )}
        </div>
    </div>
  )
}

export default MiniCrmPageContent
