import type { BasicPlan, PlanInfo } from '@/app/components/billing/type'
import { Plan, Priority } from '@/app/components/billing/type'
// Numeric limits stay aligned with `billing_saas/plan_catalog.json` (bundled copy for Next/Turbopack).
import planCatalog from '@/config/plan_catalog.json'

const supportModelProviders = 'OpenAI/Anthropic/Llama2/Azure OpenAI/Hugging Face/Replicate'

export const NUM_INFINITE = -1
export const contractSales = 'contractSales'
export const unAvailable = 'unAvailable'

export const contactSalesUrl = 'https://vikgc6bnu1s.typeform.com/dify-business'
export const getStartedWithCommunityUrl = 'https://github.com/langgenius/dify'
export const getWithPremiumUrl = 'https://aws.amazon.com/marketplace/pp/prodview-t22mebxzwjhu6'

type CatalogPlan = keyof typeof planCatalog

function vectorSpaceLabel(limitMb: number): string {
  if (limitMb >= 1024) {
    const gb = limitMb / 1024
    const rounded = Number.isInteger(gb) ? String(gb) : gb.toFixed(1)
    return `${rounded}GB`
  }
  return `${limitMb}MB`
}

function apiRateFromCatalog(limit: number): number {
  return limit <= 0 ? NUM_INFINITE : limit
}

function triggerEventsFromCatalog(limit: number): number {
  return limit <= 0 ? NUM_INFINITE : limit
}

function buildPlanInfo(plan: CatalogPlan, rest: Omit<PlanInfo, 'teamMembers' | 'buildApps' | 'documents' | 'vectorSpace' | 'apiRateLimit' | 'triggerEvents' | 'annotatedResponse'>): PlanInfo {
  const c = planCatalog[plan]
  return {
    ...rest,
    teamMembers: c.members.limit,
    buildApps: c.apps.limit,
    documents: c.documents_upload_quota.limit,
    vectorSpace: vectorSpaceLabel(c.vector_space.limit),
    apiRateLimit: apiRateFromCatalog(c.api_rate_limit.limit),
    triggerEvents: triggerEventsFromCatalog(c.trigger_event.limit),
    annotatedResponse: c.annotation_quota_limit.limit,
  }
}

export const ALL_PLANS: Record<BasicPlan, PlanInfo> = {
  sandbox: buildPlanInfo('sandbox', {
    level: 1,
    price: 0,
    modelProviders: supportModelProviders,
    teamWorkspace: 1,
    documentsUploadQuota: 0,
    documentsRequestQuota: 10,
    documentProcessingPriority: Priority.standard,
    messageRequest: 200,
    logHistory: 30,
  }),
  professional: buildPlanInfo('professional', {
    level: 2,
    price: 59,
    modelProviders: supportModelProviders,
    teamWorkspace: 1,
    documentsUploadQuota: 0,
    documentsRequestQuota: 100,
    documentProcessingPriority: Priority.priority,
    messageRequest: 5000,
    logHistory: NUM_INFINITE,
  }),
  team: buildPlanInfo('team', {
    level: 3,
    price: 159,
    modelProviders: supportModelProviders,
    teamWorkspace: 1,
    documentsUploadQuota: 0,
    documentsRequestQuota: 1000,
    documentProcessingPriority: Priority.topPriority,
    messageRequest: 10000,
    logHistory: NUM_INFINITE,
  }),
}

export const defaultPlan = {
  type: Plan.sandbox as BasicPlan,
  usage: {
    documents: planCatalog.sandbox.documents_upload_quota.limit,
    vectorSpace: 1,
    buildApps: 1,
    teamMembers: 1,
    annotatedResponse: 1,
    documentsUploadQuota: 0,
    apiRateLimit: 0,
    triggerEvents: 0,
  },
  total: {
    documents: planCatalog.sandbox.documents_upload_quota.limit,
    vectorSpace: 10,
    buildApps: planCatalog.sandbox.apps.limit,
    teamMembers: planCatalog.sandbox.members.limit,
    annotatedResponse: planCatalog.sandbox.annotation_quota_limit.limit,
    documentsUploadQuota: 0,
    apiRateLimit: ALL_PLANS.sandbox.apiRateLimit,
    triggerEvents: ALL_PLANS.sandbox.triggerEvents,
  },
  reset: {
    apiRateLimit: null,
    triggerEvents: null,
  },
}
