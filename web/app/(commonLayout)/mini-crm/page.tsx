'use client'

import type { MiniCrmLeadFormState, MiniCrmMainTab, MiniCrmViewMode } from '@/app/components/mini-crm/constants'
import type { MiniCrmFunnelAnalytics, MiniCrmLeadRow, MiniCrmStageCounts } from '@/service/tools'
import { useTranslation } from '#i18n'
import { RiContactsBookLine, RiKanbanView, RiTableLine } from '@remixicon/react'
import { Fragment, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import Loading from '@/app/components/base/loading'
import Pagination from '@/app/components/base/pagination'
import { SegmentedControl } from '@/app/components/base/segmented-control'
import { SkeletonRectangle, SkeletonRow } from '@/app/components/base/skeleton'
import TabSliderPlain from '@/app/components/base/tab-slider-plain'
import { toast } from '@/app/components/base/ui/toast'
import { leadRowToFormState, MINI_CRM_CHANNEL_TYPES, tagsInputToArray } from '@/app/components/mini-crm/constants'
import { CrmBulkToolbar } from '@/app/components/mini-crm/crm-bulk-toolbar'
import { CrmFunnelDashboard } from '@/app/components/mini-crm/crm-funnel-dashboard'
import { CrmKanbanBoard } from '@/app/components/mini-crm/crm-kanban-board'
import { CrmLeadEditor } from '@/app/components/mini-crm/crm-lead-editor'
import { CrmLeadTags } from '@/app/components/mini-crm/crm-lead-tags'
import { CrmLeadTimeline } from '@/app/components/mini-crm/crm-lead-timeline'
import { CrmRemarketingPanel } from '@/app/components/mini-crm/crm-remarketing-panel'
import { CrmSummaryBar } from '@/app/components/mini-crm/crm-summary-bar'
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

function resolveMainTabFromUrl(tab: string): MiniCrmMainTab {
  if (tab === 'analytics' || tab === 'remarketing' || tab === 'leads')
    return tab
  return 'leads'
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

const MiniCrmPageContent = () => {
  const { t, i18n } = useTranslation('common')
  const searchParams = useSearchParams()
  const urlConversationId = searchParams.get('conversation_id') ?? ''
  const urlTab = searchParams.get('tab') ?? 'leads'
  const { data: membersData } = useMembers()

  const [mainTabSelection, setMainTabSelection] = useState(() => ({
    urlTab,
    tab: resolveMainTabFromUrl(urlTab),
  }))
  const mainTab = mainTabSelection.urlTab === urlTab
    ? mainTabSelection.tab
    : resolveMainTabFromUrl(urlTab)
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
  }, [selectedChannelTypeFilter, selectedPipelineStageFilter, appliedSearchQuery, pageSize, t])

  useEffect(() => {
    void loadLeads(currentPage)
  }, [loadLeads, currentPage])

  const loadFunnelAnalytics = useCallback(async () => {
    setIsFunnelLoading(true)
    try {
      const response = await getMiniCrmFunnelAnalytics({
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
  }, [analyticsPeriodDays, selectedChannelTypeFilter, t])

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
      })
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
  }, [bulkStage, currentPage, loadLeads, selectedConversationIds, t])

  const exportAllLeads = useCallback(async () => {
    try {
      const csv = await exportMiniCrmLeadsCsv({
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
  }, [appliedSearchQuery, selectedChannelTypeFilter, selectedPipelineStageFilter, t])

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
        className={cn(
          'rounded-xl border border-divider-regular bg-background-default p-4 shadow-sm',
          isExpanded && 'ring-1 ring-components-panel-border',
        )}
      >
        <button
          type="button"
          className="w-full text-left"
          onClick={() => beginInlineEditForLeadRow(leadRow)}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="font-medium text-text-primary">{contactName}</div>
              <div className="text-xs text-text-tertiary">{leadRow.external_user_id}</div>
            </div>
            <StageTag stage={leadRow.stage} />
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
        <div className="mt-3 flex justify-end">
          <Link
            href={`/omnichannel?channel_id=${encodeURIComponent(leadRow.channel_id)}&conversation_id=${encodeURIComponent(leadRow.conversation_id)}`}
            className="text-xs font-medium text-text-accent"
            onClick={e => e.stopPropagation()}
          >
            {t('miniCrm.openInbox')}
          </Link>
        </div>
        {isExpanded && formState && (
          <div className="mt-4 border-t border-divider-subtle pt-4">
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
    <div className="relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body px-4 py-6 sm:px-8">
      <div className="mx-auto w-full max-w-6xl">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="system-xl-semibold text-text-primary">{t('miniCrm.pageTitle')}</h1>
            <p className="mt-1 max-w-2xl system-sm-regular text-text-secondary">{t('miniCrm.pageSubtitle')}</p>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-divider-regular bg-background-default px-3 py-2">
            <RiContactsBookLine className="size-5 text-text-accent" aria-hidden />
            <span className="system-xs-regular text-text-tertiary">{t('miniCrm.heroBadgeValue')}</span>
          </div>
        </div>

        <TabSliderPlain
          className="mb-4"
          value={mainTab}
          onChange={value => setMainTabSelection({ urlTab, tab: value as MiniCrmMainTab })}
          options={[
            { value: 'leads', text: t('miniCrm.tabLeads') },
            { value: 'analytics', text: t('miniCrm.tabAnalytics') },
            { value: 'remarketing', text: t('miniCrm.tabRemarketing') },
          ]}
        />

        <div className="mb-4 flex flex-wrap items-end gap-3">
          <div>
            <div className="mb-1 text-xs font-medium text-text-tertiary">{t('miniCrm.channel')}</div>
            <select
              className="h-9 min-w-[160px] rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-2 system-sm-regular text-text-primary"
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
          <CrmRemarketingPanel channelTypeFilter={selectedChannelTypeFilter} />
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

            <div className="mb-4 flex flex-wrap items-end gap-3">
              <SegmentedControl
                size="small"
                value={viewMode}
                onChange={(value) => {
                  resetLeadListPagination()
                  setViewMode(value as MiniCrmViewMode)
                }}
                options={[
                  { value: 'table', text: t('miniCrm.viewTable'), Icon: RiTableLine },
                  { value: 'kanban', text: t('miniCrm.viewKanban'), Icon: RiKanbanView },
                ]}
              />
              <div className="flex min-w-[200px] flex-1 flex-col">
                <div className="mb-1 text-xs font-medium text-text-tertiary">{t('miniCrm.filterSearchPlaceholder')}</div>
                <div className="flex gap-2">
                  <Input
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
                  <Button
                    variant="primary"
                    className="shrink-0"
                    onClick={() => {
                      resetLeadListPagination()
                      setAppliedSearchQuery(searchQueryInput.trim())
                    }}
                  >
                    {t('operation.search')}
                  </Button>
                </div>
              </div>
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

            <div className="mb-2 text-xs text-text-tertiary">{t('miniCrm.total', { count: totalLeadCount })}</div>

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
              <div className="rounded-xl border border-divider-regular bg-background-default px-6 py-12 text-center">
                <p className="text-sm text-text-secondary">{t('miniCrm.emptyLeads')}</p>
                <p className="mt-1 text-xs text-text-tertiary">{t('miniCrm.emptyLeadsHint')}</p>
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

                <div className="hidden overflow-x-auto rounded-xl border border-divider-regular bg-background-default shadow-sm md:block">
                  <table className="w-full min-w-[1100px] border-collapse text-left text-sm">
                    <thead>
                      <tr className="border-b border-divider-regular bg-background-section-burn">
                        <th className="px-3 py-2">
                          <input
                            type="checkbox"
                            checked={crmLeadRows.length > 0 && crmLeadRows.every(row => selectedConversationIds.includes(row.conversation_id))}
                            onChange={toggleSelectAllVisible}
                            aria-label={t('miniCrm.selectAll')}
                          />
                        </th>
                        <th className="px-3 py-2 font-medium text-text-secondary">{t('miniCrm.colContact')}</th>
                        <th className="px-3 py-2 font-medium text-text-secondary">{t('miniCrm.channel')}</th>
                        <th className="px-3 py-2 font-medium text-text-secondary">{t('miniCrm.colSource')}</th>
                        <th className="px-3 py-2 font-medium text-text-secondary">{t('miniCrm.colStage')}</th>
                        <th className="px-3 py-2 font-medium text-text-secondary">{t('miniCrm.colOwner')}</th>
                        <th className="px-3 py-2 font-medium text-text-secondary">{t('miniCrm.colContactInfo')}</th>
                        <th className="px-3 py-2 font-medium text-text-secondary">{t('miniCrm.tagsLabel')}</th>
                        <th className="px-3 py-2 font-medium text-text-secondary">{t('miniCrm.colUpdated')}</th>
                        <th className="px-3 py-2 font-medium text-text-secondary" />
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
                              className={cn(
                                'cursor-pointer border-b border-divider-subtle hover:bg-state-base-hover',
                                isExpanded && 'bg-state-base-hover',
                              )}
                              onClick={() => beginInlineEditForLeadRow(leadRow)}
                            >
                              <td className="px-3 py-2" onClick={e => e.stopPropagation()}>
                                <input
                                  type="checkbox"
                                  checked={selectedConversationIds.includes(leadRow.conversation_id)}
                                  onChange={() => toggleLeadSelection(leadRow.conversation_id)}
                                  aria-label={t('miniCrm.selectLead')}
                                />
                              </td>
                              <td className="px-3 py-2 text-text-primary">
                                <div className="font-medium">{contactName}</div>
                                <div className="text-xs text-text-tertiary">{leadRow.external_user_id}</div>
                                {leadRow.notes && (
                                  <div className="mt-1 line-clamp-1 text-xs text-text-quaternary">
                                    {truncateText(leadRow.notes, 80)}
                                  </div>
                                )}
                              </td>
                              <td className="px-3 py-2 text-text-secondary">
                                {(leadRow.channel_name || '').trim() || resolveOmnichannelTypeTitle(leadRow.channel_type)}
                              </td>
                              <td className="px-3 py-2 text-text-secondary">{leadRow.source_display}</td>
                              <td className="px-3 py-2">
                                <StageTag stage={leadRow.stage} />
                              </td>
                              <td className="px-3 py-2 text-text-secondary">{resolveOwnerName(leadRow.owner_account_id)}</td>
                              <td className="px-3 py-2 text-xs text-text-secondary">
                                {leadRow.contact_phone && <div>{leadRow.contact_phone}</div>}
                                {leadRow.contact_email && <div className="truncate">{leadRow.contact_email}</div>}
                                {!leadRow.contact_phone && !leadRow.contact_email && '-'}
                              </td>
                              <td className="px-3 py-2">
                                <CrmLeadTags tags={leadRow.tags} />
                              </td>
                              <td className="px-3 py-2 text-xs text-text-quaternary tabular-nums">
                                {formatRelativeTime(leadRow.crm_updated_at, i18n.language)}
                              </td>
                              <td className="px-3 py-2">
                                <Link
                                  href={`/omnichannel?channel_id=${encodeURIComponent(leadRow.channel_id)}&conversation_id=${encodeURIComponent(leadRow.conversation_id)}`}
                                  className="text-xs font-medium text-text-accent"
                                  onClick={e => e.stopPropagation()}
                                >
                                  {t('miniCrm.openInbox')}
                                </Link>
                              </td>
                            </tr>
                            {isExpanded && formState && (
                              <tr className="border-b border-divider-subtle bg-background-section-burn">
                                <td colSpan={10} className="px-3 py-3" onClick={e => e.stopPropagation()}>
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
              </>
            )}

            {!isInitialLoading && !isEmpty && (
              <div className="mt-4 overflow-hidden rounded-xl border border-divider-regular bg-background-default">
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

const MiniCrmPage = () => (
  <Suspense
    fallback={(
      <div className="flex min-h-[50vh] flex-1 items-center justify-center">
        <Loading type="app" />
      </div>
    )}
  >
    <MiniCrmPageContent />
  </Suspense>
)

export default MiniCrmPage
