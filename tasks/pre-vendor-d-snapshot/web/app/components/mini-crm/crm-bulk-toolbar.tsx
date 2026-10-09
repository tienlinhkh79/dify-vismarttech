'use client'

import { useTranslation } from '#i18n'
import { RiCheckboxMultipleLine, RiDownloadLine } from '@remixicon/react'
import { CRM_BRAND } from './crm-theme'
import { MINI_CRM_STAGES } from './constants'

type CrmBulkToolbarProps = {
  selectedCount: number
  bulkStage: string
  isApplying: boolean
  resolveStageLabel: (stage: string) => string
  onBulkStageChange: (stage: string) => void
  onApplyBulkStage: () => void
  onExportSelected: () => void
  onExportAll: () => void
  onClearSelection: () => void
}

export function CrmBulkToolbar({
  selectedCount,
  bulkStage,
  isApplying,
  resolveStageLabel,
  onBulkStageChange,
  onApplyBulkStage,
  onExportSelected,
  onExportAll,
  onClearSelection,
}: CrmBulkToolbarProps) {
  const { t } = useTranslation('common')
  const hasSelection = selectedCount > 0

  return (
    <div
      className="mb-4 flex flex-wrap items-center gap-2 rounded-lg border px-4 py-2.5 transition-all"
      style={{
        borderColor: hasSelection ? `${CRM_BRAND.primary}55` : CRM_BRAND.border,
        backgroundColor: hasSelection ? CRM_BRAND.primaryMuted : CRM_BRAND.surface,
      }}
    >
      <div className="flex items-center gap-2">
        <RiCheckboxMultipleLine
          className="size-4"
          style={{ color: hasSelection ? CRM_BRAND.primary : CRM_BRAND.textMuted }}
          aria-hidden
        />
        <span
          className="text-sm"
          style={{
            fontWeight: hasSelection ? 600 : 400,
            color: hasSelection ? CRM_BRAND.textPrimary : CRM_BRAND.textSecondary,
          }}
        >
          {t('miniCrm.bulkSelected', { count: selectedCount })}
        </span>
      </div>
      <div className="mx-1 hidden h-5 w-px sm:block" style={{ backgroundColor: CRM_BRAND.border }} />
      <select
        className="h-8 rounded-md border px-2.5 text-sm"
        style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.headerBg, color: CRM_BRAND.textPrimary }}
        value={bulkStage}
        onChange={e => onBulkStageChange(e.target.value)}
      >
        <option value="">{t('miniCrm.bulkStagePlaceholder')}</option>
        {MINI_CRM_STAGES.map(stage => (
          <option key={stage} value={stage}>{resolveStageLabel(stage)}</option>
        ))}
      </select>
      <button
        type="button"
        className="h-8 rounded-md px-3 text-xs font-semibold text-white disabled:opacity-40"
        style={{ backgroundColor: CRM_BRAND.primary }}
        disabled={!bulkStage || !selectedCount || isApplying}
        onClick={onApplyBulkStage}
      >
        {isApplying ? '…' : t('miniCrm.bulkApplyStage')}
      </button>
      <button
        type="button"
        className="inline-flex h-8 items-center rounded-md border px-3 text-xs font-semibold disabled:opacity-40"
        style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textSecondary, backgroundColor: CRM_BRAND.surface }}
        disabled={!selectedCount}
        onClick={onExportSelected}
      >
        <RiDownloadLine className="mr-1 size-3.5" aria-hidden />
        {t('miniCrm.exportSelected')}
      </button>
      <button
        type="button"
        className="inline-flex h-8 items-center rounded-md border px-3 text-xs font-semibold"
        style={{ borderColor: CRM_BRAND.border, color: CRM_BRAND.textSecondary, backgroundColor: CRM_BRAND.surface }}
        onClick={onExportAll}
      >
        <RiDownloadLine className="mr-1 size-3.5" aria-hidden />
        {t('miniCrm.exportAll')}
      </button>
      {hasSelection && (
        <button
          type="button"
          className="h-8 px-2 text-xs font-medium"
          style={{ color: CRM_BRAND.textMuted }}
          onClick={onClearSelection}
        >
          {t('miniCrm.clearSelection')}
        </button>
      )}
    </div>
  )
}
