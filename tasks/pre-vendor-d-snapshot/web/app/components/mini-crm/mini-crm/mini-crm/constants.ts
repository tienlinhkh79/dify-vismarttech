export const MINI_CRM_STAGES = ['new', 'qualified', 'won', 'lost'] as const

export type MiniCrmStage = typeof MINI_CRM_STAGES[number]

export const MINI_CRM_BUSINESS_LINES = ['restaurant', 'nail'] as const

export type MiniCrmBusinessLine = typeof MINI_CRM_BUSINESS_LINES[number]

export const MINI_CRM_CHANNEL_TYPES = [
  'facebook_messenger',
  'instagram_dm',
  'tiktok_messaging',
  'zalo_oa',
  'zalo_personal',
  'website_widget',
] as const

export const MINI_CRM_PRESET_TAGS = [
  'VIP',
  'New customer',
  'Ticket',
  'Zalo care',
] as const

export type MiniCrmViewMode = 'table' | 'kanban'

export type MiniCrmMainTab = 'leads' | 'analytics' | 'remarketing'

export const MINI_CRM_TAB_HREFS: Record<MiniCrmMainTab, string> = {
  leads: '/mini-crm/restaurant/leads',
  analytics: '/mini-crm/restaurant/analytics',
  remarketing: '/mini-crm/restaurant/remarketing',
}

export function miniCrmTabHref(vertical: MiniCrmBusinessLine, tab: MiniCrmMainTab): string {
  return `/mini-crm/${vertical}/${tab}`
}

export function resolveBusinessLineFromPath(segment: string | null | undefined): MiniCrmBusinessLine | null {
  if (segment === 'restaurant' || segment === 'nail')
    return segment
  return null
}

export function resolveMainTabFromPath(tab: string | null | undefined): MiniCrmMainTab {
  if (tab === 'analytics' || tab === 'remarketing' || tab === 'leads')
    return tab
  return 'leads'
}

export function resolveVerticalAndTabFromPathname(pathname: string): {
  businessLine: MiniCrmBusinessLine
  mainTab: MiniCrmMainTab
} {
  const segments = pathname.split('/').filter(Boolean)
  const idx = segments.indexOf('mini-crm')
  const verticalSegment = idx >= 0 ? segments[idx + 1] : null
  const tabSegment = idx >= 0 ? segments[idx + 2] : null
  const businessLine = resolveBusinessLineFromPath(verticalSegment) ?? 'restaurant'
  const mainTab = resolveMainTabFromPath(tabSegment ?? verticalSegment)
  return { businessLine, mainTab }
}

export type MiniCrmLeadFormState = {
  stage: string
  notes: string
  source_override: string
  owner_account_id: string | null
  tags_input: string
  contact_phone: string
  contact_email: string
}

export function tagsInputToArray(tagsInput: string): string[] {
  return tagsInput
    .split(/[,;]/)
    .map(tag => tag.trim())
    .filter(Boolean)
}

export function tagsArrayToInput(tags: string[] | null | undefined): string {
  return (tags || []).join(', ')
}

export function leadRowToFormState(leadRow: {
  stage: string
  notes?: string | null
  source_override?: string | null
  owner_account_id?: string | null
  tags?: string[] | null
  contact_phone?: string | null
  contact_email?: string | null
}): MiniCrmLeadFormState {
  return {
    stage: leadRow.stage,
    notes: leadRow.notes || '',
    source_override: leadRow.source_override || '',
    owner_account_id: leadRow.owner_account_id ?? null,
    tags_input: tagsArrayToInput(leadRow.tags),
    contact_phone: leadRow.contact_phone || '',
    contact_email: leadRow.contact_email || '',
  }
}
