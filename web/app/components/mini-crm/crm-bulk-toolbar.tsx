'use client'

import { useTranslation } from '#i18n'
import Button from '@/app/components/base/button'
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

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-divider-regular bg-background-default px-3 py-2">
      <span className="text-sm text-text-secondary">
        {t('miniCrm.bulkSelected', { count: selectedCount })}
      </span>
      <select
        className="h-8 rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-2 text-sm text-text-primary"
        value={bulkStage}
        onChange={e => onBulkStageChange(e.target.value)}
      >
        <option value="">{t('miniCrm.bulkStagePlaceholder')}</option>
        {MINI_CRM_STAGES.map(stage => (
          <option key={stage} value={stage}>{resolveStageLabel(stage)}</option>
        ))}
      </select>
      <Button
        variant="primary"
        size="small"
        disabled={!bulkStage || !selectedCount}
        loading={isApplying}
        onClick={onApplyBulkStage}
      >
        {t('miniCrm.bulkApplyStage')}
      </Button>
      <Button variant="secondary" size="small" disabled={!selectedCount} onClick={onExportSelected}>
        {t('miniCrm.exportSelected')}
      </Button>
      <Button variant="secondary" size="small" onClick={onExportAll}>
        {t('miniCrm.exportAll')}
      </Button>
      {selectedCount > 0 && (
        <Button variant="ghost" size="small" onClick={onClearSelection}>
          {t('miniCrm.clearSelection')}
        </Button>
      )}
    </div>
  )
}
