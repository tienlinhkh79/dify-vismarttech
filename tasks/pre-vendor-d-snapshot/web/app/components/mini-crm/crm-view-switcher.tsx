'use client'

import type { MiniCrmViewMode } from './constants'
import { useTranslation } from '#i18n'
import { RiKanbanView, RiTableLine } from '@remixicon/react'
import { cn } from '@/utils/classnames'
import { CRM_BRAND } from './crm-theme'

type CrmViewSwitcherProps = {
  value: MiniCrmViewMode
  onChange: (mode: MiniCrmViewMode) => void
}

const VIEWS: { value: MiniCrmViewMode, icon: typeof RiTableLine, labelKey: string }[] = [
  { value: 'table', icon: RiTableLine, labelKey: 'miniCrm.viewTable' },
  { value: 'kanban', icon: RiKanbanView, labelKey: 'miniCrm.viewKanban' },
]

export function CrmViewSwitcher({ value, onChange }: CrmViewSwitcherProps) {
  const { t } = useTranslation('common')

  return (
    <div
      className="inline-flex rounded-lg border p-0.5"
      style={{ borderColor: CRM_BRAND.border, backgroundColor: CRM_BRAND.headerBg }}
      role="group"
      aria-label={t('miniCrm.viewTable')}
    >
      {VIEWS.map(({ value: viewValue, icon: Icon, labelKey }) => {
        const isActive = value === viewValue
        return (
          <button
            key={viewValue}
            type="button"
            onClick={() => onChange(viewValue)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-all',
            )}
            style={{
              backgroundColor: isActive ? CRM_BRAND.surface : 'transparent',
              color: isActive ? CRM_BRAND.primaryDark : CRM_BRAND.textMuted,
              boxShadow: isActive ? `inset 0 0 0 1px ${CRM_BRAND.primary}` : undefined,
            }}
          >
            <Icon className="size-3.5" aria-hidden />
            {t(labelKey as 'miniCrm.viewTable')}
          </button>
        )
      })}
    </div>
  )
}
