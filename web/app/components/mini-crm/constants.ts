export const MINI_CRM_STAGES = ['new', 'qualified', 'won', 'lost'] as const

export type MiniCrmStage = typeof MINI_CRM_STAGES[number]

export const MINI_CRM_CHANNEL_TYPES = [
  'facebook_messenger',
  'instagram_dm',
  'tiktok_messaging',
  'zalo_oa',
] as const

export const MINI_CRM_PRESET_TAGS = [
  'VIP',
  'New customer',
  'Ticket',
  'Zalo care',
] as const

export type MiniCrmViewMode = 'table' | 'kanban'

export type MiniCrmMainTab = 'leads' | 'analytics' | 'remarketing'

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
