import type { MiniCrmStage } from './constants'

/** Attio / Pipedrive-inspired CRM design tokens (not Dify console tokens). */
export const CRM_BRAND = {
  primary: '#0D9488',
  primaryDark: '#0F766E',
  primaryMuted: '#CCFBF1',
  workspace: '#F4F5F7',
  surface: '#FFFFFF',
  border: '#E8EAED',
  borderStrong: '#D1D5DB',
  textPrimary: '#1A1D21',
  textSecondary: '#6B7280',
  textMuted: '#9CA3AF',
  headerBg: '#FAFBFC',
} as const

export type CrmStageTheme = {
  color: string
  bgColor: string
  borderColor: string
  chartColor: string
}

export const CRM_STAGE_THEME: Record<MiniCrmStage, CrmStageTheme> = {
  new: {
    color: '#4F46E5',
    bgColor: '#E0E7FF',
    borderColor: '#4F46E5',
    chartColor: '#4F46E5',
  },
  qualified: {
    color: '#0D9488',
    bgColor: '#CCFBF1',
    borderColor: '#0D9488',
    chartColor: '#0D9488',
  },
  won: {
    color: '#16A34A',
    bgColor: '#DCFCE7',
    borderColor: '#16A34A',
    chartColor: '#16A34A',
  },
  lost: {
    color: '#DC2626',
    bgColor: '#FEE2E2',
    borderColor: '#DC2626',
    chartColor: '#DC2626',
  },
}

export const CRM_CHART_AXIS = {
  label: '#6B7280',
  splitLine: '#E5E7EB',
  tooltipBg: '#1A1D21',
  gridBorder: CRM_BRAND.border,
}

export function resolveStageTheme(stage: string): CrmStageTheme {
  return CRM_STAGE_THEME[stage as MiniCrmStage] ?? {
    color: '#64748B',
    bgColor: '#F1F5F9',
    borderColor: '#64748B',
    chartColor: '#64748B',
  }
}

export function getContactInitials(name: string): string {
  const trimmed = name.trim()
  if (!trimmed)
    return '?'
  const parts = trimmed.split(/\s+/).filter(Boolean)
  if (parts.length >= 2)
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
  return trimmed.slice(0, 2).toUpperCase()
}
