import type {
  Collection,
  Credential,
  CustomCollectionBackend,
  CustomParamSchema,
  Tool,
  ToolCredential,
  WorkflowToolProviderRequest,
  WorkflowToolProviderResponse,
} from '@/app/components/tools/types'
import { buildProviderQuery } from './_tools_util'
import { del, get, patch, post, upload } from './base'

export type MessengerChannel = {
  id?: string
  channel_id: string
  platform?: string
  channel_type?: string
  status?: 'active' | 'inactive'
  app_id: string
  name: string
  page_id: string
  verify_token?: string
  app_secret?: string
  page_access_token?: string
  verify_token_masked?: string
  app_secret_masked?: string
  page_access_token_masked?: string
  graph_api_version: string
  enabled: boolean
  webhook_path?: string
  created_at?: string
  updated_at?: string
}

export type ChannelProvider = {
  provider: 'messenger' | 'instagram' | 'tiktok' | 'zalo' | string
  channel_type: string
  display_name: string
  status: 'active' | 'coming_soon'
  setup_kind: string
}

export type Channel = {
  id?: string
  channel_id: string
  channel_type: string
  platform: string
  status?: 'active' | 'inactive'
  app_id: string
  name: string
  external_resource_id: string
  verify_token?: string
  client_secret?: string
  access_token?: string
  oauth_application_id?: string | null
  oauth_status?: 'pending_auth' | 'connected' | 'expired' | string
  oauth_callback_url?: string
  verify_token_masked?: string
  client_secret_masked?: string
  access_token_masked?: string
  api_version: string
  enabled: boolean
  zalo_auto_reply_enabled?: boolean
  zalo_info_card_enabled?: boolean
  zalo_info_card_title?: string | null
  zalo_info_card_subtitle?: string | null
  zalo_info_card_image_url?: string | null
  personal_login_status?: string
  webhook_path?: string
  created_at?: string
  updated_at?: string
  /** Populated when listing with ``include_branding`` (Graph / Zalo OA). */
  external_resource_picture_url?: string | null
}

type MessengerChannelListResponse = {
  data: MessengerChannel[]
}

type MessengerChannelItemResponse = {
  data: MessengerChannel
}

type ChannelProviderResponse = {
  data: ChannelProvider[]
}

type ChannelListResponse = {
  data: Channel[]
}

type ChannelItemResponse = {
  data: Channel
}

export type OmnichannelConversation = {
  id: string
  external_user_id: string
  participant_display_name?: string | null
  participant_profile_pic_url?: string | null
  last_message_at?: string
  last_message_preview?: string | null
  channel_id: string
  channel_type: string
  status?: 'open' | 'resolved' | 'pending' | 'snoozed'
  assignee_account_id?: string | null
  unread_count?: number
  agent_last_seen_at?: string | null
  snoozed_until?: string | null
  created_at?: string
  updated_at?: string
}

export type OmnichannelCannedResponse = {
  id: string
  title: string
  content: string
  shortcut?: string | null
  created_at?: string
  updated_at?: string
}

export type OmnichannelMessage = {
  id: string
  conversation_id: string
  external_user_id: string
  external_message_id?: string
  direction: 'inbound' | 'outbound'
  source: 'webhook' | 'sync' | 'system' | 'internal_note' | 'agent'
  content: string
  attachments: Array<Record<string, unknown>>
  metadata: Record<string, unknown>
  sender_display_name?: string | null
  sender_profile_pic_url?: string | null
  channel_actor_name?: string | null
  channel_actor_picture_url?: string | null
  quote_preview?: {
    zalo_msg_id?: string
    omnichannel_message_id?: string
    content?: string
    direction?: string
  } | null
  system_note?: boolean
  created_at?: string
}

export type ZaloBridgeFailedJob = {
  id: string
  channel_id: string
  kind: string
  dedup_key: string
  attempts: number
  max_attempts: number
  last_error?: string
  created_at?: string
  updated_at?: string
}

export type OmnichannelSyncJob = {
  id: string
  tenant_id: string
  channel_id: string
  channel_type: string
  status: 'pending' | 'running' | 'succeeded' | 'failed'
  progress: number
  total_messages: number
  synced_messages: number
  last_error?: string
  since_at?: string
  until_at?: string
  started_at?: string
  finished_at?: string
  created_at?: string
  updated_at?: string
}

type OmnichannelListResponse<T> = {
  data: T[]
  has_more: boolean
  next_cursor: string | null
}

type OmnichannelItemResponse<T> = {
  data: T
}

export type KiotVietConnection = {
  id?: string
  connection_id: string
  platform?: string
  status?: 'active' | 'inactive'
  name: string
  client_id: string
  client_secret?: string
  client_secret_masked?: string
  retailer_name: string
  enabled: boolean
  created_at?: string
  updated_at?: string
}

type KiotVietConnectionListResponse = {
  data: KiotVietConnection[]
}

type KiotVietConnectionItemResponse = {
  data: KiotVietConnection
}

export const fetchCollectionList = () => {
  return get<Collection[]>('/workspaces/current/tool-providers')
}

export const fetchBuiltInToolList = (collectionName: string) => {
  return get<Tool[]>(`/workspaces/current/tool-provider/builtin/${collectionName}/tools`)
}

export const fetchCustomToolList = (collectionName: string) => {
  const query = buildProviderQuery(collectionName)
  return get<Tool[]>(`/workspaces/current/tool-provider/api/tools?${query}`)
}

export const fetchModelToolList = (collectionName: string) => {
  const query = buildProviderQuery(collectionName)
  return get<Tool[]>(`/workspaces/current/tool-provider/model/tools?${query}`)
}

export const fetchWorkflowToolList = (appID: string) => {
  return get<Tool[]>(`/workspaces/current/tool-provider/workflow/tools?workflow_tool_id=${appID}`)
}

export const fetchBuiltInToolCredentialSchema = (collectionName: string) => {
  return get<ToolCredential[]>(`/workspaces/current/tool-provider/builtin/${collectionName}/credentials_schema`)
}

export const fetchBuiltInToolCredential = (collectionName: string) => {
  return get<Record<string, unknown>>(`/workspaces/current/tool-provider/builtin/${collectionName}/credentials`)
}
export const updateBuiltInToolCredential = (collectionName: string, credential: Record<string, unknown>) => {
  return post(`/workspaces/current/tool-provider/builtin/${collectionName}/update`, {
    body: {
      credentials: credential,
    },
  })
}

export const removeBuiltInToolCredential = (collectionName: string) => {
  return post(`/workspaces/current/tool-provider/builtin/${collectionName}/delete`, {
    body: {},
  })
}

export const getMessengerOAuthAuthorizationUrl = (payload: {
  app_id: string
  app_secret: string
  graph_api_version?: string
}) => {
  return post<{ authorization_url: string }>('/workspaces/current/tool-provider/builtin/messenger/oauth/authorization-url', {
    body: payload,
  })
}

export const listMessengerChannels = () => {
  return get<MessengerChannelListResponse>('/workspaces/current/channels/messenger')
}

export const listChannelProviders = () => {
  return get<ChannelProviderResponse>('/workspaces/current/channels/providers')
}

export const listChannels = (params?: { include_branding?: boolean }) => {
  const queryParams = params?.include_branding ? { include_branding: 'true' } : {}
  const mapLegacyMessengerToChannel = (item: MessengerChannel): Channel => ({
    id: item.id,
    channel_id: item.channel_id,
    channel_type: item.channel_type || 'facebook_messenger',
    platform: item.platform || 'messenger',
    status: item.status,
    app_id: item.app_id,
    name: item.name,
    external_resource_id: item.page_id,
    verify_token: item.verify_token,
    client_secret: item.app_secret,
    access_token: item.page_access_token,
    verify_token_masked: item.verify_token_masked,
    client_secret_masked: item.app_secret_masked,
    access_token_masked: item.page_access_token_masked,
    api_version: item.graph_api_version,
    enabled: item.enabled,
    webhook_path: item.webhook_path,
    created_at: item.created_at,
    updated_at: item.updated_at,
    external_resource_picture_url: null,
  })

  return get<ChannelListResponse>('/workspaces/current/channels', {
    params: queryParams,
  }).catch(async (error) => {
    // Backward compatibility: older API deployments only expose messenger channels endpoints.
    if (!(error instanceof Response) || ![404, 405].includes(error.status))
      throw error
    const legacy = await listMessengerChannels()
    return {
      data: (legacy.data || []).map(mapLegacyMessengerToChannel),
    }
  })
}

export const createChannel = (payload: Channel, options?: { silent?: boolean }) => {
  return post<ChannelItemResponse>(
    '/workspaces/current/channels',
    { body: payload },
    options?.silent ? { silent: true } : {},
  )
}

export const updateChannel = (channelId: string, payload: Partial<Channel>, options?: { silent?: boolean }) => {
  return patch<ChannelItemResponse>(
    `/workspaces/current/channels/${channelId}`,
    { body: payload },
    options?.silent ? { silent: true } : {},
  )
}

export const deleteChannel = (channelId: string) => {
  return del<{ result: string }>(`/workspaces/current/channels/${channelId}`)
}

export type ZaloOAuthStartResponse = {
  auth_url: string
  qr_data_uri: string
  state: string
  expires_in: number
  oauth_callback_url: string
}

export const startZaloChannelOAuth = (channelId: string) => {
  return post<{ data: ZaloOAuthStartResponse }>(
    `/workspaces/current/channels/zalo/${channelId}/oauth/start`,
    { body: {} },
  )
}

export const getZaloChannelOAuthStatus = (channelId: string) => {
  return get<{
    data: {
      connected: boolean
      oauth_status: string
      expires_at?: string | null
      oauth_callback_url: string
    }
  }>(`/workspaces/current/channels/zalo/${channelId}/oauth/status`)
}

export const refreshOmnichannelConversationParticipant = (channelId: string, conversationId: string) => {
  return post<OmnichannelItemResponse<OmnichannelConversation>>(
    `/workspaces/current/channels/${channelId}/conversations/${conversationId}/refresh-participant`,
    {},
  )
}

export type MiniCrmLeadRow = {
  lead_id?: string | null
  conversation_id: string
  channel_id: string
  channel_type: string
  channel_name: string
  external_user_id: string
  participant_display_name?: string | null
  last_message_at?: string | null
  last_message_preview?: string | null
  stage: string
  owner_account_id?: string | null
  notes?: string | null
  source_override?: string | null
  source_display: string
  tags?: string[]
  contact_phone?: string | null
  contact_email?: string | null
  crm_updated_at?: string | null
}

export type MiniCrmStageCounts = {
  new: number
  qualified: number
  won: number
  lost: number
}

export type MiniCrmLeadsResponse = {
  data: MiniCrmLeadRow[]
  total: number
  offset: number
  limit: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
  stage_counts?: MiniCrmStageCounts
}

export const listMiniCrmLeads = (params?: {
  channel_type?: string
  stage?: string
  /** Plain-text filter; sent as query param ``q`` for backward-compatible REST. */
  search_query?: string
  /** 1-based page number (preferred). */
  page?: number
  page_size?: number
  /** Legacy offset-based pagination. Ignored when ``page`` is set. */
  page_offset?: number
}) => {
  const { search_query, page, page_size, page_offset, channel_type, stage } = params ?? {}
  return get<MiniCrmLeadsResponse>('/workspaces/current/mini-crm/leads', {
    params: {
      channel_type,
      stage,
      q: search_query,
      page,
      page_size,
      offset: page !== undefined ? undefined : page_offset,
      limit: page_size,
    },
  })
}

export const getMiniCrmLead = (conversationId: string) => {
  return get<{ data: MiniCrmLeadRow }>(`/workspaces/current/mini-crm/leads/${encodeURIComponent(conversationId)}`)
}

export const patchMiniCrmLead = (conversationId: string, body: {
  stage?: string
  owner_account_id?: string | null
  notes?: string | null
  notes_append?: string | null
  source_override?: string | null
  tags?: string[] | null
  contact_phone?: string | null
  contact_email?: string | null
}) => {
  return patch<{ data: MiniCrmLeadRow }>(`/workspaces/current/mini-crm/leads/${encodeURIComponent(conversationId)}`, {
    body,
  })
}

export const bulkPatchMiniCrmLeads = (body: {
  conversation_ids: string[]
  stage?: string
  owner_account_id?: string | null
  tags?: string[] | null
}) => {
  return patch<{ data: MiniCrmLeadRow[], count: number }>('/workspaces/current/mini-crm/leads/bulk', {
    body,
  })
}

export const exportMiniCrmLeadsCsv = async (params?: {
  channel_type?: string
  stage?: string
  search_query?: string
}) => {
  const { search_query, channel_type, stage } = params ?? {}
  const response = await get<Response>(
    '/workspaces/current/mini-crm/leads/export',
    {
      params: {
        channel_type,
        stage,
        q: search_query,
      },
    },
    { needAllResponseContent: true },
  )
  if (!response.ok)
    throw new Error('export failed')
  return response.text()
}

export type MiniCrmTimelineItem = {
  kind: 'activity' | 'message'
  id: string
  activity_type: string
  summary: string
  payload?: Record<string, unknown> | null
  actor_account_id?: string | null
  at?: string | null
}

export type MiniCrmDailyPipelinePoint = {
  date: string
  won: number
  lost: number
  qualified: number
}

export type MiniCrmChannelBreakdownItem = {
  channel_type: string
  count: number
}

export type MiniCrmFunnelAnalytics = {
  stage_counts: MiniCrmStageCounts
  total: number
  period_days: number
  recent_won: number
  recent_lost: number
  conversion: {
    new_to_qualified_pct: number
    qualified_to_won_pct: number
    overall_win_pct: number
  }
  funnel_steps: Array<{ stage: string, count: number }>
  daily_pipeline: MiniCrmDailyPipelinePoint[]
  channel_breakdown: MiniCrmChannelBreakdownItem[]
}

export type MiniCrmRemarketingSegment = {
  key: string
  title_key?: string
  description_key?: string
  lead_count?: number
}

export const listMiniCrmLeadTimeline = (conversationId: string, params?: { limit?: number }) => {
  return get<{ data: MiniCrmTimelineItem[] }>(
    `/workspaces/current/mini-crm/leads/${encodeURIComponent(conversationId)}/timeline`,
    { params: { limit: params?.limit } },
  )
}

export const getMiniCrmFunnelAnalytics = (params?: {
  channel_type?: string
  period_days?: number
}) => {
  return get<MiniCrmFunnelAnalytics>('/workspaces/current/mini-crm/analytics/funnel', {
    params: {
      channel_type: params?.channel_type,
      period_days: params?.period_days,
    },
  })
}

export const listMiniCrmRemarketingSegments = (params?: { channel_type?: string }) => {
  return get<{ data: MiniCrmRemarketingSegment[] }>('/workspaces/current/mini-crm/remarketing/segments', {
    params: { channel_type: params?.channel_type },
  })
}

export const exportMiniCrmRemarketingSegmentCsv = async (
  segmentKey: string,
  params?: { channel_type?: string },
) => {
  const response = await get<Response>(
    `/workspaces/current/mini-crm/remarketing/segments/${encodeURIComponent(segmentKey)}/export`,
    {
      params: {
        channel_type: params?.channel_type,
      },
    },
    { needAllResponseContent: true },
  )
  if (!response.ok)
    throw new Error('export failed')
  return response.text()
}

export const listOmnichannelConversations = (channelId: string, params?: {
  since?: string
  until?: string
  cursor?: string
  limit?: number
  status?: OmnichannelConversation['status']
  assignee_account_id?: string
  unassigned_only?: boolean
}) => {
  return get<OmnichannelListResponse<OmnichannelConversation>>(`/workspaces/current/channels/${channelId}/conversations`, {
    params,
  })
}

export const listAllOmnichannelConversations = (params?: {
  channel_id?: string
  since?: string
  until?: string
  cursor?: string
  limit?: number
  status?: OmnichannelConversation['status']
  assignee_account_id?: string
  unassigned_only?: boolean
}) => {
  return get<OmnichannelListResponse<OmnichannelConversation>>('/workspaces/current/omnichannel/conversations', {
    params,
  })
}

export const createOmnichannelConversation = (channelId: string, body: { external_user_id: string }) => {
  return post<OmnichannelItemResponse<OmnichannelConversation>>(
    `/workspaces/current/channels/${encodeURIComponent(channelId)}/conversations`,
    { body },
  )
}

export type OmnichannelMediaUpload = {
  url: string
  attachment_type: 'image' | 'video' | 'audio' | 'file'
  file_id: string
  name: string
}

export const uploadOmnichannelMedia = (
  file: File,
  onProgress?: (percent: number) => void,
): Promise<OmnichannelMediaUpload> => {
  const formData = new FormData()
  formData.append('file', file)
  return upload(
    {
      xhr: new XMLHttpRequest(),
      data: formData,
      onprogress: onProgress
        ? (e) => {
            if (e.lengthComputable)
              onProgress(Math.floor(e.loaded / e.total * 100))
          }
        : undefined,
    },
    false,
    '/workspaces/current/omnichannel/media-upload',
  ).then(res => (res as unknown as { data: OmnichannelMediaUpload }).data)
}

export const sendOmnichannelAgentMessage = (
  channelId: string,
  conversationId: string,
  body: {
    text: string
    attachment_url?: string
    attachment_type?: 'image' | 'video' | 'audio' | 'file'
    quote_message_id?: string
  },
) => {
  return post<OmnichannelItemResponse<{ id: string, conversation_id: string, channel_type: string }>>(
    `/workspaces/current/channels/${encodeURIComponent(channelId)}/conversations/${encodeURIComponent(conversationId)}/messages`,
    { body },
  )
}

export const patchOmnichannelConversation = (
  channelId: string,
  conversationId: string,
  body: {
    status?: OmnichannelConversation['status']
    assignee_account_id?: string | null
    clear_assignee?: boolean
  },
) => {
  return patch<OmnichannelItemResponse<OmnichannelConversation>>(
    `/workspaces/current/channels/${encodeURIComponent(channelId)}/conversations/${encodeURIComponent(conversationId)}`,
    { body },
  )
}

export const markOmnichannelConversationSeen = (channelId: string, conversationId: string) => {
  return post<OmnichannelItemResponse<OmnichannelConversation>>(
    `/workspaces/current/channels/${encodeURIComponent(channelId)}/conversations/${encodeURIComponent(conversationId)}/mark-seen`,
    { body: {} },
    { silent: true },
  )
}

export const sendOmnichannelInternalNote = (
  channelId: string,
  conversationId: string,
  body: { text: string },
) => {
  return post<OmnichannelItemResponse<{ id: string }>>(
    `/workspaces/current/channels/${encodeURIComponent(channelId)}/conversations/${encodeURIComponent(conversationId)}/internal-notes`,
    { body },
  )
}

export const listOmnichannelCannedResponses = () => {
  return get<{ data: OmnichannelCannedResponse[] }>('/workspaces/current/omnichannel/canned-responses')
}

export const createOmnichannelCannedResponse = (body: {
  title: string
  content: string
  shortcut?: string
}) => {
  return post<{ data: OmnichannelCannedResponse }>('/workspaces/current/omnichannel/canned-responses', { body })
}

export const deleteOmnichannelCannedResponse = (responseId: string) => {
  return del<{ result: string }>(`/workspaces/current/omnichannel/canned-responses/${encodeURIComponent(responseId)}`)
}

export const listOmnichannelMessages = (channelId: string, conversationId: string, params?: {
  since?: string
  until?: string
  cursor?: string
  limit?: number
}) => {
  return get<OmnichannelListResponse<OmnichannelMessage>>(
    `/workspaces/current/channels/${channelId}/conversations/${conversationId}/messages`,
    { params },
  )
}

export const listZaloBridgeFailedJobs = (channelId: string, params?: { limit?: number }) => {
  return get<{ data: ZaloBridgeFailedJob[] }>(
    `/workspaces/current/channels/${encodeURIComponent(channelId)}/zalo-bridge-jobs/failed`,
    { params },
  )
}

export const retryZaloBridgeJob = (channelId: string, jobId: string) => {
  return post<{ result: string }>(
    `/workspaces/current/channels/${encodeURIComponent(channelId)}/zalo-bridge-jobs/${encodeURIComponent(jobId)}/retry`,
    { body: {} },
  )
}

export const provisionZaloPersonalChannel = () => {
  return post<{ data: Channel }>(
    '/workspaces/current/channels/zalo-personal/provision',
    { body: {} },
  )
}

export const provisionZaloOaChannel = (payload: {
  oauth_application_id: string
  client_secret: string
}) => {
  return post<{ data: Channel }>(
    '/workspaces/current/channels/zalo-oa/provision',
    { body: payload },
  )
}

export const provisionOAuthChannel = (payload: { channel_type: string }) => {
  return post<{ data: Channel }>(
    '/workspaces/current/channels/oauth/provision',
    { body: payload },
  )
}

export const startZaloPersonalLogin = (channelId: string) => {
  return post<{ data: { qr_data_uri: string, status: string } }>(
    `/workspaces/current/channels/zalo-personal/${encodeURIComponent(channelId)}/login/start`,
    { body: {} },
  )
}

export const getZaloPersonalLoginStatus = (channelId: string) => {
  return get<{ data: { status: string, connected: boolean } }>(
    `/workspaces/current/channels/zalo-personal/${encodeURIComponent(channelId)}/login/status`,
  )
}

export const startOmnichannelHistorySync = (channelId: string, payload: {
  since?: string
  until?: string
}) => {
  return post<OmnichannelItemResponse<OmnichannelSyncJob>>(`/workspaces/current/channels/${channelId}/sync-history`, {
    body: payload,
  })
}

export const getOmnichannelSyncJob = (channelId: string, jobId: string) => {
  return get<OmnichannelItemResponse<OmnichannelSyncJob>>(`/workspaces/current/channels/${channelId}/sync-jobs/${jobId}`)
}

export const getOmnichannelStats = (channelId: string, params?: { since?: string, until?: string }) => {
  return get<OmnichannelItemResponse<{
    total_messages: number
    inbound_messages: number
    outbound_messages: number
    active_conversations: number
  }>>(`/workspaces/current/channels/${channelId}/stats`, { params })
}

export const getOmnichannelHealth = (channelId: string) => {
  return get<OmnichannelItemResponse<{
    channel_id: string
    enabled: boolean
    channel_type: string
    last_inbound_at?: string
    last_outbound_at?: string
    webhook_path: string
  }>>(`/workspaces/current/channels/${channelId}/health`)
}

export const testOmnichannelWebhook = (channelId: string) => {
  return post<OmnichannelItemResponse<{
    success: boolean
    channel_id: string
    channel_type: string
    message: string
  }>>(`/workspaces/current/channels/${channelId}/webhook/test`)
}

export const createMessengerChannel = (payload: MessengerChannel) => {
  return post<MessengerChannelItemResponse>('/workspaces/current/channels/messenger', {
    body: payload,
  })
}

export const updateMessengerChannel = (
  channelId: string,
  payload: Partial<MessengerChannel>,
) => {
  return patch<MessengerChannelItemResponse>(`/workspaces/current/channels/messenger/${channelId}`, {
    body: payload,
  })
}

// Backward-compatible aliases used by existing callers.
export const listMessengerOmnichannelChannels = listMessengerChannels
export const createMessengerOmnichannelChannel = createMessengerChannel
export const updateMessengerOmnichannelChannel = updateMessengerChannel

export const listKiotVietConnections = () => {
  return get<KiotVietConnectionListResponse>('/workspaces/current/channels/kiotviet')
}

export const createKiotVietConnection = (payload: KiotVietConnection) => {
  return post<KiotVietConnectionItemResponse>('/workspaces/current/channels/kiotviet', {
    body: payload,
  })
}

export const updateKiotVietConnection = (connectionId: string, payload: Partial<KiotVietConnection>) => {
  return patch<KiotVietConnectionItemResponse>(`/workspaces/current/channels/kiotviet/${connectionId}`, {
    body: payload,
  })
}

export const parseParamsSchema = (schema: string) => {
  return post<{ parameters_schema: CustomParamSchema[], schema_type: string }>('/workspaces/current/tool-provider/api/schema', {
    body: {
      schema,
    },
  })
}

export const fetchCustomCollection = (collectionName: string) => {
  const query = buildProviderQuery(collectionName)
  return get<CustomCollectionBackend>(`/workspaces/current/tool-provider/api/get?${query}`)
}

export const createCustomCollection = (collection: CustomCollectionBackend) => {
  return post('/workspaces/current/tool-provider/api/add', {
    body: {
      ...collection,
    },
  })
}

export const updateCustomCollection = (collection: CustomCollectionBackend) => {
  return post('/workspaces/current/tool-provider/api/update', {
    body: {
      ...collection,
    },
  })
}

export const removeCustomCollection = (collectionName: string) => {
  return post('/workspaces/current/tool-provider/api/delete', {
    body: {
      provider: collectionName,
    },
  })
}

export const importSchemaFromURL = (url: string) => {
  return get('/workspaces/current/tool-provider/api/remote', {
    params: {
      url,
    },
  })
}

export const testAPIAvailable = (payload: {
  provider_name: string
  tool_name: string
  credentials: Credential
  schema_type: string
  schema: string
  parameters: Record<string, string>
}) => {
  return post('/workspaces/current/tool-provider/api/test/pre', {
    body: {
      ...payload,
    },
  })
}

export const createWorkflowToolProvider = (payload: WorkflowToolProviderRequest & { workflow_app_id: string }) => {
  return post('/workspaces/current/tool-provider/workflow/create', {
    body: { ...payload },
  })
}

export const saveWorkflowToolProvider = (payload: WorkflowToolProviderRequest & Partial<{
  workflow_app_id: string
  workflow_tool_id: string
}>) => {
  return post('/workspaces/current/tool-provider/workflow/update', {
    body: { ...payload },
  })
}

export const fetchWorkflowToolDetail = (toolID: string) => {
  return get<WorkflowToolProviderResponse>(`/workspaces/current/tool-provider/workflow/get?workflow_tool_id=${toolID}`)
}

export const deleteWorkflowTool = (toolID: string) => {
  return post('/workspaces/current/tool-provider/workflow/delete', {
    body: {
      workflow_tool_id: toolID,
    },
  })
}
