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
import { get, patch, post } from './base'

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
  webhook_path?: string
  created_at?: string
  updated_at?: string
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
  channel_id: string
  channel_type: string
  created_at?: string
  updated_at?: string
}

export type OmnichannelMessage = {
  id: string
  conversation_id: string
  external_user_id: string
  external_message_id?: string
  direction: 'inbound' | 'outbound'
  source: 'webhook' | 'sync' | 'system'
  content: string
  attachments: Array<Record<string, unknown>>
  metadata: Record<string, unknown>
  sender_display_name?: string | null
  sender_profile_pic_url?: string | null
  channel_actor_name?: string | null
  channel_actor_picture_url?: string | null
  created_at?: string
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

export const listChannels = () => {
  return get<ChannelListResponse>('/workspaces/current/channels')
}

export const createChannel = (payload: Channel) => {
  return post<ChannelItemResponse>('/workspaces/current/channels', {
    body: payload,
  })
}

export const updateChannel = (channelId: string, payload: Partial<Channel>) => {
  return patch<ChannelItemResponse>(`/workspaces/current/channels/${channelId}`, {
    body: payload,
  })
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
  stage: string
  owner_account_id?: string | null
  notes?: string | null
  source_override?: string | null
  source_display: string
  crm_updated_at?: string | null
}

export type MiniCrmLeadsResponse = {
  data: MiniCrmLeadRow[]
  total: number
  offset: number
  limit: number
}

export const listMiniCrmLeads = (params?: {
  channel_type?: string
  stage?: string
  /** Plain-text filter; sent as query param ``q`` for backward-compatible REST. */
  search_query?: string
  page_offset?: number
  page_size?: number
}) => {
  const { search_query, page_offset, page_size, channel_type, stage } = params ?? {}
  return get<MiniCrmLeadsResponse>('/workspaces/current/mini-crm/leads', {
    params: {
      channel_type,
      stage,
      q: search_query,
      offset: page_offset,
      limit: page_size,
    },
  })
}

export const patchMiniCrmLead = (conversationId: string, body: {
  stage?: string
  owner_account_id?: string | null
  notes?: string | null
  source_override?: string | null
}) => {
  return patch<{ data: MiniCrmLeadRow }>(`/workspaces/current/mini-crm/leads/${encodeURIComponent(conversationId)}`, {
    body,
  })
}

export const listOmnichannelConversations = (channelId: string, params?: {
  since?: string
  until?: string
  cursor?: string
  limit?: number
}) => {
  return get<OmnichannelListResponse<OmnichannelConversation>>(`/workspaces/current/channels/${channelId}/conversations`, {
    params,
  })
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

export const getOmnichannelStats = (channelId: string, params?: { since?: string; until?: string }) => {
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
