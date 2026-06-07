'use client'
import type { ChangeEvent, ReactNode } from 'react'
import type { SetupStep } from './channels-ui'
import type { Channel, ChannelProvider } from '@/service/tools'
import { RiEyeLine, RiEyeOffLine } from '@remixicon/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
// eslint-disable-next-line no-restricted-imports -- migrate to ui/select in follow-up
import PureSelect from '@/app/components/base/select/pure'
import {
  Dialog,
  DialogCloseButton,
  DialogContent,
  DialogTitle,
} from '@/app/components/base/ui/dialog'
import { toast } from '@/app/components/base/ui/toast'
import { API_PREFIX } from '@/config'
import { openOAuthPopup } from '@/hooks/use-oauth'
import {
  createChannel,
  deleteChannel,
  getMessengerOAuthAuthorizationUrl,
  listChannelProviders,
  listChannels,
  provisionOAuthChannel,
  provisionZaloOaChannel,
  provisionZaloPersonalChannel,
  updateChannel,
} from '@/service/tools'
import { useAppList } from '@/service/use-apps'
import { getProviderSetupConfig } from './channel-setup-config'
import {
  ChannelItem,
  ProviderSummaryCard,
  SetupManualHint,
  SetupNavigation,
  SetupProgress,
  SetupProviderSelector,
  SetupSection,

} from './channels-ui'
import ZaloOAuthModal from './zalo-oauth-modal'
import ZaloOAuthPanel from './zalo-oauth-panel'
import ZaloPersonalQrModal from './zalo-personal-qr-modal'
import ZaloPersonalQrPanel from './zalo-personal-qr-panel'

const buildMessengerOAuthCallbackUrl = (): string => {
  const suffix = '/workspaces/current/tool-provider/builtin/messenger/oauth/callback'
  const prefix = API_PREFIX.replace(/\/$/, '')
  if (prefix.startsWith('http://') || prefix.startsWith('https://'))
    return `${prefix}${suffix}`
  if (typeof window === 'undefined')
    return ''
  const path = prefix.startsWith('/') ? prefix : `/${prefix}`
  return `${window.location.origin}${path}${suffix}`
}

const FieldGroup = ({ label, hint, children }: { label: string, hint?: string, children: ReactNode }) => (
  <div className="space-y-1">
    <div className="system-xs-medium text-text-secondary">{label}</div>
    {children}
    {hint && <div className="system-xs-regular text-text-tertiary">{hint}</div>}
  </div>
)

/** `post()` throws a cloned `Response` on HTTP errors (see `fetch.ts`). */
async function toastChannelApiError(err: unknown, fallback: string) {
  if (err instanceof Response) {
    const data = (await err.json().catch(() => null)) as { error?: string, message?: string } | null
    const msg = data?.message || data?.error
    toast.error(msg || fallback)
    return
  }
  toast.error(fallback)
}

const ChannelsPage = () => {
  const MESSENGER_OAUTH_APP_ID_STORAGE_KEY = 'dify_messenger_oauth_app_id'
  const { t } = useTranslation()
  const [providers, setProviders] = useState<ChannelProvider[]>([])
  const [channels, setChannels] = useState<Channel[]>([])
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false)
  const [setupStep, setSetupStep] = useState<SetupStep>(1)
  const [editingChannelId, setEditingChannelId] = useState<string | null>(null)
  const [isConnectingFacebook, setIsConnectingFacebook] = useState(false)
  const [zaloOAuthChannelId, setZaloOAuthChannelId] = useState<string | null>(null)
  const [zaloOAuthOpen, setZaloOAuthOpen] = useState(false)
  const [zaloPersonalChannelId, setZaloPersonalChannelId] = useState<string | null>(null)
  const [zaloPersonalOpen, setZaloPersonalOpen] = useState(false)
  const [zaloPersonalDraftId, setZaloPersonalDraftId] = useState<string | null>(null)
  const [zaloPersonalQrConnected, setZaloPersonalQrConnected] = useState(false)
  const [zaloPersonalProvisioning, setZaloPersonalProvisioning] = useState(false)
  const [zaloOaDraftId, setZaloOaDraftId] = useState<string | null>(null)
  const [zaloOaOAuthConnected, setZaloOaOAuthConnected] = useState(false)
  const [zaloOaProvisioning, setZaloOaProvisioning] = useState(false)
  const [metaOAuthDraftId, setMetaOAuthDraftId] = useState<string | null>(null)
  const [metaOAuthProvisioning, setMetaOAuthProvisioning] = useState(false)
  const [zaloOaCallbackUrl, setZaloOaCallbackUrl] = useState('')
  const [isVerifyTokenVisible, setIsVerifyTokenVisible] = useState(false)
  const [isClientSecretVisible, setIsClientSecretVisible] = useState(false)
  const [isAccessTokenVisible, setIsAccessTokenVisible] = useState(false)
  const [oauthPages, setOauthPages] = useState<Array<{ id: string, name: string, access_token: string }>>([])
  /** Page IDs selected after Facebook OAuth (create flow). Meta: one Page = one channel + one page access token. */
  const [selectedMessengerPageIds, setSelectedMessengerPageIds] = useState<string[]>([])
  /** When creating multiple Messenger channels at once, each Page can route to a different Studio app. */
  const [messengerTargetAppByPageId, setMessengerTargetAppByPageId] = useState<Record<string, string>>({})
  const [messengerApplyAllDraft, setMessengerApplyAllDraft] = useState('')
  const [messengerAuthAppId, setMessengerAuthAppId] = useState(() => (typeof window !== 'undefined' ? window.localStorage.getItem(MESSENGER_OAUTH_APP_ID_STORAGE_KEY) || '' : ''))
  const [messengerAuthAppSecret, setMessengerAuthAppSecret] = useState('')
  const [appOrigin] = useState(() => (typeof window !== 'undefined' ? window.location.origin : ''))
  const [maskedSecrets, setMaskedSecrets] = useState<{
    verify_token?: string
    client_secret?: string
    access_token?: string
  }>({})
  const [isSavingChannel, setIsSavingChannel] = useState(false)
  const [formValue, setFormValue] = useState<Channel>({
    channel_type: 'facebook_messenger',
    channel_id: '',
    app_id: '',
    name: '',
    external_resource_id: '',
    verify_token: '',
    client_secret: '',
    access_token: '',
    oauth_application_id: '',
    api_version: 'v23.0',
    enabled: true,
    zalo_auto_reply_enabled: false,
    zalo_info_card_enabled: false,
    zalo_info_card_title: '',
    zalo_info_card_subtitle: '',
    zalo_info_card_image_url: '',
    platform: 'messenger',
  })
  const { data: appListRes } = useAppList({ page: 1, limit: 100, mode: 'all' }, { enabled: true })
  const appOptions = appListRes?.data || []

  const generateVerifyToken = () => `vk_${Math.random().toString(36).slice(2, 12)}`

  const ensureDefaultProviders = useCallback((providerList: ChannelProvider[]) => {
    const defaults: ChannelProvider[] = [
      {
        provider: 'messenger',
        channel_type: 'facebook_messenger',
        display_name: t('settings.channelsProviderDisplayMessenger', { ns: 'common' }),
        status: 'active',
        setup_kind: 'oauth_or_token',
      },
      {
        provider: 'instagram',
        channel_type: 'instagram_dm',
        display_name: t('settings.channelsProviderDisplayInstagram', { ns: 'common' }),
        status: 'active',
        setup_kind: 'oauth_meta',
      },
      {
        provider: 'tiktok',
        channel_type: 'tiktok_messaging',
        display_name: t('settings.channelsProviderDisplayTikTok', { ns: 'common' }),
        status: 'active',
        setup_kind: 'oauth_tiktok',
      },
      {
        provider: 'zalo',
        channel_type: 'zalo_oa',
        display_name: t('settings.channelsProviderDisplayZalo', { ns: 'common' }),
        status: 'active',
        setup_kind: 'oauth_zalo',
      },
      {
        provider: 'zalo_personal',
        channel_type: 'zalo_personal',
        display_name: t('settings.channelsProviderDisplayZaloPersonal', { ns: 'common' }),
        status: 'active',
        setup_kind: 'qr_zalo_personal',
      },
    ]
    const defaultByType = new Map(defaults.map(item => [item.channel_type, item]))
    const normalizedFromApi: ChannelProvider[] = providerList.map((provider) => {
      const matchedDefault = defaultByType.get(provider.channel_type)
      return matchedDefault
        ? { ...provider, ...matchedDefault, status: provider.status || matchedDefault.status }
        : { ...provider, status: provider.status || 'active' }
    })
    const existingTypes = new Set(normalizedFromApi.map(item => item.channel_type))
    const merged: ChannelProvider[] = [...normalizedFromApi]
    defaults.forEach((provider) => {
      if (!existingTypes.has(provider.channel_type))
        merged.push(provider)
    })
    return merged
  }, [t])

  const loadChannels = useCallback(async () => {
    try {
      const [channelsRes, providersRes] = await Promise.all([listChannels(), listChannelProviders()])
      setProviders(ensureDefaultProviders(providersRes.data || []))
      setChannels(channelsRes.data || [])
    }
    catch {
      setProviders(ensureDefaultProviders([]))
      setChannels([])
    }
  }, [ensureDefaultProviders])

  useEffect(() => {
    void loadChannels()
  }, [loadChannels])

  const openCreate = (channelType?: string) => {
    const preferredChannelType = channelType || providers[0]?.channel_type || 'facebook_messenger'
    const provider = providers.find((item: ChannelProvider) => item.channel_type === preferredChannelType)
    setEditingChannelId(null)
    setFormValue({
      channel_type: preferredChannelType,
      channel_id: '',
      app_id: '',
      name: '',
      external_resource_id: preferredChannelType === 'zalo_personal' ? 'personal' : '',
      verify_token: generateVerifyToken(),
      client_secret: '',
      access_token: '',
      oauth_application_id: '',
      api_version: 'v23.0',
      enabled: true,
      zalo_auto_reply_enabled: false,
      zalo_info_card_enabled: false,
      zalo_info_card_title: '',
      zalo_info_card_subtitle: '',
      zalo_info_card_image_url: '',
      platform: provider?.provider || 'messenger',
    })
    setOauthPages([])
    setSelectedMessengerPageIds([])
    setMessengerTargetAppByPageId({})
    setMessengerApplyAllDraft('')
    if (typeof window !== 'undefined') {
      setMessengerAuthAppId(window.localStorage.getItem(MESSENGER_OAUTH_APP_ID_STORAGE_KEY) || '')
    }
    else {
      setMessengerAuthAppId('')
    }
    setMessengerAuthAppSecret('')
    setMaskedSecrets({})
    setZaloPersonalDraftId(null)
    setZaloPersonalQrConnected(false)
    setZaloPersonalProvisioning(false)
    setZaloOaDraftId(null)
    setZaloOaOAuthConnected(false)
    setZaloOaProvisioning(false)
    setZaloOaCallbackUrl('')
    setMetaOAuthDraftId(null)
    setMetaOAuthProvisioning(false)
    setIsVerifyTokenVisible(false)
    setIsClientSecretVisible(false)
    setIsAccessTokenVisible(false)
    setSetupStep(1)
    setIsConfigModalOpen(true)
  }

  const openEdit = (channel: Channel) => {
    const maskedVerifyToken = channel.verify_token_masked || ''
    const maskedClientSecret = channel.client_secret_masked || ''
    const maskedAccessToken = channel.access_token_masked || ''
    setEditingChannelId(channel.channel_id)
    setFormValue({
      ...channel,
      verify_token: maskedVerifyToken,
      client_secret: maskedClientSecret,
      access_token: maskedAccessToken,
      oauth_application_id: channel.oauth_application_id || '',
    })
    setOauthPages(channel.external_resource_id
      ? [{
          id: channel.external_resource_id,
          name: channel.name || channel.channel_id,
          access_token: '',
        }]
      : [])
    setSelectedMessengerPageIds(channel.external_resource_id ? [String(channel.external_resource_id)] : [])
    if (typeof window !== 'undefined') {
      setMessengerAuthAppId(window.localStorage.getItem(MESSENGER_OAUTH_APP_ID_STORAGE_KEY) || '')
    }
    else {
      setMessengerAuthAppId('')
    }
    setMessengerAuthAppSecret('')
    setMaskedSecrets({
      verify_token: maskedVerifyToken,
      client_secret: maskedClientSecret,
      access_token: maskedAccessToken,
    })
    setIsVerifyTokenVisible(false)
    setIsClientSecretVisible(false)
    setIsAccessTokenVisible(false)
    setSetupStep(3)
    setIsConfigModalOpen(true)
  }

  const isEditing = !!editingChannelId
  const isMessengerProvider = formValue.channel_type === 'facebook_messenger'
  const isZaloOaProvider = formValue.channel_type === 'zalo_oa'
  const isZaloPersonalProvider = formValue.channel_type === 'zalo_personal'
  const isMetaOAuthProvider = formValue.channel_type === 'instagram_dm' || formValue.channel_type === 'tiktok_messaging'
  const isZaloPersonalDraftCreate = !isEditing && isZaloPersonalProvider && !!zaloPersonalDraftId
  const isZaloOaDraftCreate = !isEditing && isZaloOaProvider && !!zaloOaDraftId
  const isMetaOAuthDraftCreate = !isEditing && isMetaOAuthProvider && !!metaOAuthDraftId
  const editingChannel = useMemo(
    () => channels.find((c: Channel) => c.channel_id === editingChannelId),
    [channels, editingChannelId],
  )
  const providerSetupConfig = getProviderSetupConfig(formValue.channel_type)
  const providerDocsUrl = providerSetupConfig.docsUrl
  const editClientSecretHint = useMemo(() => {
    const base = isZaloOaProvider
      ? t('settings.channelsZaloAppSecretHint', { ns: 'common' })
      : t('settings.channelsGenericClientSecretHint', { ns: 'common' })
    if (isEditing && maskedSecrets.client_secret)
      return `${base} (${t('settings.channelsStoredCredentialHint', { ns: 'common' })}: ${maskedSecrets.client_secret})`
    return base
  }, [isZaloOaProvider, isEditing, maskedSecrets.client_secret, t])
  const editAccessTokenHint = useMemo(() => {
    const base = isZaloOaProvider
      ? t('settings.channelsZaloTokenHint', { ns: 'common' })
      : t('settings.channelsGenericAccessTokenHint', { ns: 'common' })
    if (isEditing && maskedSecrets.access_token)
      return `${base} (${t('settings.channelsStoredCredentialHint', { ns: 'common' })}: ${maskedSecrets.access_token})`
    return base
  }, [isZaloOaProvider, isEditing, maskedSecrets.access_token, t])
  const providerChannelCountMap = channels.reduce<Record<string, number>>((acc: Record<string, number>, channel: Channel) => {
    acc[channel.channel_type] = (acc[channel.channel_type] || 0) + 1
    return acc
  }, {})
  const usePerPageMessengerStudioApps
    = !isEditing && isMessengerProvider && selectedMessengerPageIds.length > 1 && oauthPages.length > 0

  useEffect(() => {
    if (!usePerPageMessengerStudioApps)
      return
    queueMicrotask(() => setMessengerTargetAppByPageId((prev) => {
      const next = { ...prev }
      const seed = formValue.app_id.trim()
      for (const id of selectedMessengerPageIds) {
        if (next[id] === undefined)
          next[id] = seed
      }
      for (const k of Object.keys(next)) {
        if (!selectedMessengerPageIds.includes(k))
          delete next[k]
      }
      return next
    }))
  }, [usePerPageMessengerStudioApps, selectedMessengerPageIds.join(','), formValue.app_id])

  useEffect(() => {
    if (!isConfigModalOpen || isEditing || setupStep !== 2 || !isZaloPersonalProvider || zaloPersonalDraftId)
      return
    let cancelled = false
    const run = async () => {
      setZaloPersonalProvisioning(true)
      try {
        const res = await provisionZaloPersonalChannel()
        if (cancelled)
          return
        const draftId = res.data.channel_id
        setZaloPersonalDraftId(draftId)
        setFormValue((prev: Channel) => ({
          ...prev,
          channel_id: draftId,
          platform: 'zalo_personal',
          external_resource_id: 'personal',
        }))
      }
      catch (err) {
        if (!cancelled)
          await toastChannelApiError(err, t('settings.channelsZaloPersonalProvisionError', { ns: 'common' }))
      }
      finally {
        if (!cancelled)
          setZaloPersonalProvisioning(false)
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [isConfigModalOpen, isEditing, setupStep, isZaloPersonalProvider, zaloPersonalDraftId, t])

  useEffect(() => {
    if (!isConfigModalOpen || isEditing || setupStep !== 2 || !isMetaOAuthProvider || metaOAuthDraftId)
      return
    let cancelled = false
    const run = async () => {
      setMetaOAuthProvisioning(true)
      try {
        const res = await provisionOAuthChannel({ channel_type: formValue.channel_type })
        if (cancelled)
          return
        const draftId = res.data.channel_id
        const provider = providers.find((item: ChannelProvider) => item.channel_type === formValue.channel_type)
        setMetaOAuthDraftId(draftId)
        setFormValue((prev: Channel) => ({
          ...prev,
          channel_id: draftId,
          platform: provider?.provider || prev.platform,
          external_resource_id: prev.external_resource_id || 'pending',
        }))
      }
      catch (err) {
        if (!cancelled)
          await toastChannelApiError(err, t('settings.channelsOAuthProvisionError', { ns: 'common' }))
      }
      finally {
        if (!cancelled)
          setMetaOAuthProvisioning(false)
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [formValue.channel_type, isConfigModalOpen, isEditing, isMetaOAuthProvider, metaOAuthDraftId, providers, setupStep, t])

  const handleStartZaloOaAuthorize = useCallback(async () => {
    if (zaloOaProvisioning || zaloOaDraftId)
      return
    const appId = (formValue.oauth_application_id || '').trim()
    const secret = (formValue.client_secret || '').trim()
    if (!appId) {
      toast.error(t('settings.channelsZaloOAuthAppIdRequired', { ns: 'common' }))
      return
    }
    if (!secret) {
      toast.error(t('settings.channelsZaloOaSecretRequired', { ns: 'common' }))
      return
    }
    setZaloOaProvisioning(true)
    try {
      const res = await provisionZaloOaChannel({
        oauth_application_id: appId,
        client_secret: secret,
      })
      setZaloOaDraftId(res.data.channel_id)
      setFormValue((prev: Channel) => ({
        ...prev,
        channel_id: res.data.channel_id,
        platform: 'zalo',
        external_resource_id: '',
      }))
    }
    catch (err) {
      await toastChannelApiError(err, t('settings.channelsZaloOaProvisionError', { ns: 'common' }))
    }
    finally {
      setZaloOaProvisioning(false)
    }
  }, [formValue.client_secret, formValue.oauth_application_id, t, zaloOaDraftId, zaloOaProvisioning])

  const canGoStep2 = isEditing || !!formValue.channel_type
  const canGoStep3 = isEditing
    || (isMessengerProvider
      ? oauthPages.length > 0 && selectedMessengerPageIds.length > 0
      : isZaloPersonalProvider
        ? zaloPersonalQrConnected
        : isZaloOaProvider
          ? zaloOaOAuthConnected
          : !!formValue.client_secret?.trim() && (!providerSetupConfig.requiresAccessToken || !!formValue.access_token?.trim()))
  const isFormStepVisible = isEditing || setupStep === 3
  const webhookPathPreview = formValue.channel_id
    ? `/triggers/${formValue.platform || 'messenger'}/webhook/${formValue.channel_id}`
    : ''
  const webhookUrlPreview = webhookPathPreview && appOrigin ? `${appOrigin}${webhookPathPreview}` : ''
  const messengerOauthCallbackUrlPreview = useMemo(() => buildMessengerOAuthCallbackUrl(), [])
  const providerOptions = useMemo(
    () => providers.map(provider => ({
      value: provider.channel_type,
      label: provider.display_name,
    })),
    [providers],
  )
  const appOptionsForSelect = useMemo(
    () => appOptions.map(app => ({ value: app.id, label: app.name })),
    [appOptions],
  )
  const buildMessengerWebhookUrlForPageId = useCallback(
    (pageId: string) => {
      const path = `/triggers/${formValue.platform || 'messenger'}/webhook/messenger-${pageId}`
      return appOrigin ? `${appOrigin}${path}` : path
    },
    [appOrigin, formValue.platform],
  )
  const saveChannel = async () => {
    if (isSavingChannel)
      return
    if (!usePerPageMessengerStudioApps && !formValue.app_id.trim()) {
      toast.error(t('settings.channelsRequiredError', { ns: 'common' }))
      return
    }
    const messengerBulkCreate = !isEditing && isMessengerProvider && oauthPages.length > 0 && selectedMessengerPageIds.length > 0
    if (!messengerBulkCreate) {
      const needsExternalId = !isZaloPersonalProvider
      const needsChannelIdInput = !isZaloPersonalDraftCreate && !isZaloOaDraftCreate && !isMetaOAuthDraftCreate
      if ((needsChannelIdInput && !formValue.channel_id.trim()) || !formValue.name.trim() || (needsExternalId && !formValue.external_resource_id.trim() && !isZaloOaDraftCreate)) {
        toast.error(t('settings.channelsRequiredError', { ns: 'common' }))
        return
      }
    }
    if (isZaloPersonalDraftCreate && !zaloPersonalQrConnected) {
      toast.error(t('settings.channelsZaloPersonalQrRequired', { ns: 'common' }))
      return
    }
    if (isZaloOaDraftCreate && !zaloOaOAuthConnected) {
      toast.error(t('settings.channelsZaloOaOAuthRequired', { ns: 'common' }))
      return
    }
    if (isZaloOaDraftCreate && (!formValue.external_resource_id.trim() || formValue.external_resource_id.trim() === 'pending')) {
      toast.error(t('settings.channelsRequiredError', { ns: 'common' }))
      return
    }
    if (!isEditing && !isZaloPersonalProvider && !isMetaOAuthDraftCreate && (!formValue.verify_token?.trim() || !formValue.client_secret?.trim())) {
      toast.error(t('settings.channelsSecretRequiredError', { ns: 'common' }))
      return
    }
    if (!isEditing && providerSetupConfig.requiresAccessToken && !formValue.access_token?.trim()) {
      toast.error(t('settings.channelsProviderTokenRequiredError', { ns: 'common' }))
      return
    }
    if (!isEditing && isZaloOaProvider && !isZaloOaDraftCreate && !(formValue.oauth_application_id || '').trim()) {
      toast.error(t('settings.channelsZaloOAuthAppIdRequired', { ns: 'common' }))
      return
    }
    if (!isEditing && isZaloPersonalProvider && !formValue.external_resource_id.trim())
      formValue.external_resource_id = 'personal'
    if (!isEditing && isMessengerProvider && (!oauthPages.length || selectedMessengerPageIds.length === 0)) {
      toast.error(t('settings.channelsMessengerConnectRequired', { ns: 'common' }))
      return
    }
    const hasStoredClientSecret = !!(maskedSecrets.client_secret && String(maskedSecrets.client_secret).trim())
    const hasStoredAccessToken = !!(maskedSecrets.access_token && String(maskedSecrets.access_token).trim())
    if (
      providerSetupConfig.requiresClientSecret
      && !formValue.client_secret?.trim()
      && !(isEditing && hasStoredClientSecret)
    ) {
      toast.error(t('settings.channelsProviderSecretRequiredError', { ns: 'common' }))
      return
    }
    if (
      providerSetupConfig.requiresAccessToken
      && !formValue.access_token?.trim()
      && !(isEditing && hasStoredAccessToken)
    ) {
      toast.error(t('settings.channelsProviderTokenRequiredError', { ns: 'common' }))
      return
    }
    setIsSavingChannel(true)
    try {
      if (messengerBulkCreate) {
        const idsToCreate = selectedMessengerPageIds.filter((id) => {
          const cid = `messenger-${id}`
          return !channels.some(c => c.channel_id === cid)
        })
        if (!idsToCreate.length) {
          toast.error(t('settings.channelsMessengerAllPagesAlreadyConnected', { ns: 'common' }))
          return
        }
        const skipped = selectedMessengerPageIds.length - idsToCreate.length
        const apiVersion = formValue.api_version.trim() || 'v23.0'
        const verifyTokenInput = formValue.verify_token!.trim()
        const clientSecretInput = formValue.client_secret!.trim()
        try {
          for (const pageId of idsToCreate) {
            const page = oauthPages.find(p => String(p.id) === String(pageId))
            if (!page?.access_token?.trim()) {
              toast.error(t('settings.channelsMessengerPageTokenMissing', { ns: 'common' }))
              return
            }
            const pageName = (page.name || `Page ${page.id}`).trim() || `Page ${page.id}`
            const targetApp = usePerPageMessengerStudioApps
              ? (messengerTargetAppByPageId[String(pageId)] || '').trim()
              : formValue.app_id.trim()
            if (!targetApp) {
              toast.error(
                t('settings.channelsMessengerAppRequiredPerPage', { ns: 'common', page: pageName }),
              )
              return
            }
            await createChannel({
              channel_type: 'facebook_messenger',
              channel_id: `messenger-${page.id}`,
              app_id: targetApp,
              name: pageName,
              external_resource_id: String(page.id),
              verify_token: verifyTokenInput,
              client_secret: clientSecretInput,
              access_token: page.access_token,
              api_version: apiVersion,
              enabled: formValue.enabled,
              platform: 'messenger',
            } as Channel, { silent: true })
          }
        }
        catch (err) {
          await toastChannelApiError(err, t('settings.channelsMessengerBulkCreateError', { ns: 'common' }))
          return
        }
        if (idsToCreate.length > 1)
          toast.success(t('settings.channelsMessengerBulkCreated', { count: idsToCreate.length, ns: 'common' }))
        else
          toast.success(t('api.actionSuccess', { ns: 'common' }))
        if (skipped > 0)
          toast.error(t('settings.channelsMessengerSkippedExisting', { count: skipped, ns: 'common' }))
        setIsConfigModalOpen(false)
        await loadChannels()
        return
      }
      const payload: Partial<Channel> = {
        channel_type: formValue.channel_type,
        channel_id: formValue.channel_id.trim(),
        app_id: formValue.app_id.trim(),
        name: formValue.name.trim(),
        external_resource_id: isZaloPersonalProvider ? 'personal' : formValue.external_resource_id.trim(),
        api_version: formValue.api_version.trim() || 'v23.0',
        enabled: formValue.enabled,
      }
      const verifyTokenInput = formValue.verify_token?.trim() || ''
      const clientSecretInput = formValue.client_secret?.trim() || ''
      const accessTokenInput = formValue.access_token?.trim() || ''
      const storedVerifyToken = maskedSecrets.verify_token?.trim() || ''
      const storedClientSecret = maskedSecrets.client_secret?.trim() || ''
      const storedAccessToken = maskedSecrets.access_token?.trim() || ''

      if (verifyTokenInput && (!isEditing || verifyTokenInput !== storedVerifyToken))
        payload.verify_token = verifyTokenInput
      if (clientSecretInput && (!isEditing || clientSecretInput !== storedClientSecret))
        payload.client_secret = clientSecretInput
      if (accessTokenInput && (!isEditing || accessTokenInput !== storedAccessToken))
        payload.access_token = accessTokenInput
      if (isZaloOaProvider && (formValue.oauth_application_id || '').trim())
        payload.oauth_application_id = String(formValue.oauth_application_id).trim()
      if (isZaloOaProvider) {
        payload.zalo_auto_reply_enabled = !!formValue.zalo_auto_reply_enabled
        payload.zalo_info_card_enabled = !!formValue.zalo_info_card_enabled
        if ((formValue.zalo_info_card_title || '').trim())
          payload.zalo_info_card_title = formValue.zalo_info_card_title!.trim()
        if ((formValue.zalo_info_card_subtitle || '').trim())
          payload.zalo_info_card_subtitle = formValue.zalo_info_card_subtitle!.trim()
        if ((formValue.zalo_info_card_image_url || '').trim())
          payload.zalo_info_card_image_url = formValue.zalo_info_card_image_url!.trim()
      }
      if (formValue.platform)
        payload.platform = formValue.platform

      const openZaloOAuthAfterSave = !isEditing && isZaloOaProvider && !isZaloOaDraftCreate && !formValue.access_token?.trim()

      if (isZaloOaDraftCreate) {
        try {
          await updateChannel(zaloOaDraftId!, {
            name: formValue.name.trim(),
            app_id: formValue.app_id.trim(),
            external_resource_id: formValue.external_resource_id.trim(),
            enabled: formValue.enabled,
            zalo_auto_reply_enabled: !!formValue.zalo_auto_reply_enabled,
            zalo_info_card_enabled: !!formValue.zalo_info_card_enabled,
            ...(formValue.zalo_info_card_title?.trim()
              ? { zalo_info_card_title: formValue.zalo_info_card_title.trim() }
              : {}),
            ...(formValue.zalo_info_card_subtitle?.trim()
              ? { zalo_info_card_subtitle: formValue.zalo_info_card_subtitle.trim() }
              : {}),
            ...(formValue.zalo_info_card_image_url?.trim()
              ? { zalo_info_card_image_url: formValue.zalo_info_card_image_url.trim() }
              : {}),
          }, { silent: true })
        }
        catch (err) {
          await toastChannelApiError(err, t('api.actionFailed', { ns: 'common' }))
          return
        }
        toast.success(t('api.actionSuccess', { ns: 'common' }))
        setIsConfigModalOpen(false)
        setZaloOaDraftId(null)
        setZaloOaOAuthConnected(false)
        setZaloOaCallbackUrl('')
        await loadChannels()
        return
      }

      if (isMetaOAuthDraftCreate) {
        try {
          await updateChannel(metaOAuthDraftId!, {
            name: formValue.name.trim(),
            app_id: formValue.app_id.trim(),
            external_resource_id: formValue.external_resource_id.trim(),
            enabled: formValue.enabled,
            ...(clientSecretInput ? { client_secret: clientSecretInput } : {}),
            ...(accessTokenInput ? { access_token: accessTokenInput } : {}),
          }, { silent: true })
        }
        catch (err) {
          await toastChannelApiError(err, t('api.actionFailed', { ns: 'common' }))
          return
        }
        toast.success(t('api.actionSuccess', { ns: 'common' }))
        setIsConfigModalOpen(false)
        setMetaOAuthDraftId(null)
        await loadChannels()
        return
      }

      if (isZaloPersonalDraftCreate) {
        try {
          await updateChannel(zaloPersonalDraftId!, {
            name: formValue.name.trim(),
            app_id: formValue.app_id.trim(),
            enabled: formValue.enabled,
          }, { silent: true })
        }
        catch (err) {
          await toastChannelApiError(err, t('api.actionFailed', { ns: 'common' }))
          return
        }
        toast.success(t('api.actionSuccess', { ns: 'common' }))
        setIsConfigModalOpen(false)
        setZaloPersonalDraftId(null)
        setZaloPersonalQrConnected(false)
        await loadChannels()
        return
      }
      if (isZaloPersonalProvider && !isEditing) {
        payload.verify_token = verifyTokenInput || generateVerifyToken()
        payload.client_secret = clientSecretInput || `zp_${Math.random().toString(36).slice(2, 12)}`
        payload.access_token = ''
      }

      if (isEditing) {
        try {
          await updateChannel(editingChannelId!, payload, { silent: true })
        }
        catch (err) {
          await toastChannelApiError(err, t('api.actionFailed', { ns: 'common' }))
          return
        }
      }
      else {
        try {
          await createChannel(payload as Channel, { silent: true })
        }
        catch (err) {
          await toastChannelApiError(err, t('api.actionFailed', { ns: 'common' }))
          return
        }
      }

      toast.success(t('api.actionSuccess', { ns: 'common' }))
      setIsConfigModalOpen(false)
      await loadChannels()
      if (openZaloOAuthAfterSave) {
        setZaloOAuthChannelId(formValue.channel_id.trim())
        setZaloOAuthOpen(true)
      }
    }
    finally {
      setIsSavingChannel(false)
    }
  }

  const handleConnectFacebook = async () => {
    setIsConnectingFacebook(true)
    try {
      const messengerAppId = messengerAuthAppId.trim()
      const messengerAppSecret = messengerAuthAppSecret.trim()
      const graphApiVersion = String(formValue.api_version || 'v23.0').trim() || 'v23.0'
      if (!messengerAppId || !messengerAppSecret) {
        toast.error(t('settings.channelsFacebookCredentialRequired', { ns: 'common' }))
        return
      }
      // Facebook App Secret should be app-level secret, not a user/page access token.
      if (messengerAppSecret.startsWith('EAAT')) {
        toast.error(t('settings.channelsFacebookAppSecretFormatError', { ns: 'common' }))
        return
      }
      if (typeof window !== 'undefined')
        window.localStorage.setItem(MESSENGER_OAUTH_APP_ID_STORAGE_KEY, messengerAppId)

      const res = await getMessengerOAuthAuthorizationUrl({
        app_id: messengerAppId,
        app_secret: messengerAppSecret,
        graph_api_version: graphApiVersion,
      })
      if (!res.authorization_url) {
        toast.error(t('settings.channelsFacebookAuthorizationStartError', { ns: 'common' }))
        return
      }
      openOAuthPopup(res.authorization_url, (data) => {
        if (!data?.success) {
          toast.error(data?.errorDescription || data?.error?.message || data?.error || t('settings.channelsFacebookAuthorizationFailed', { ns: 'common' }))
          return
        }
        const pages = data?.messenger_oauth?.pages || []
        if (!pages.length) {
          toast.error(t('settings.channelsFacebookNoPagesFound', { ns: 'common' }))
          return
        }
        setOauthPages(pages)
        setSelectedMessengerPageIds(pages.map((p: { id: string }) => String(p.id)))
        const firstPage = pages[0]
        setFormValue((prev: Channel) => ({
          ...prev,
          external_resource_id: String(firstPage.id),
          access_token: String(firstPage.access_token),
          client_secret: messengerAppSecret,
          verify_token: prev.verify_token || generateVerifyToken(),
          name: prev.name || String(firstPage.name || ''),
          channel_id: prev.channel_id || `messenger-${firstPage.id}`,
          api_version: data?.messenger_oauth?.graph_api_version || graphApiVersion,
        }))
        toast.success(t('settings.channelsFacebookConnected', { ns: 'common' }))
      })
    }
    finally {
      setIsConnectingFacebook(false)
    }
  }

  const syncMessengerFormToSelectedPageIds = (nextIds: string[]) => {
    if (nextIds.length === 0 || !oauthPages.length) {
      if (!editingChannelId) {
        setFormValue((prev: Channel) => ({
          ...prev,
          channel_id: '',
          external_resource_id: '',
          name: '',
          access_token: '',
        }))
      }
      return
    }
    const first = oauthPages.find(p => String(p.id) === nextIds[0])
    if (!first)
      return
    setFormValue((prev: Channel) => ({
      ...prev,
      channel_id: editingChannelId ? prev.channel_id : `messenger-${first.id}`,
      name: editingChannelId ? prev.name : (first.name || prev.name),
      external_resource_id: first.id,
      access_token: first.access_token,
    }))
  }

  const applyMessengerPageSelection = (nextIds: string[]) => {
    setSelectedMessengerPageIds(nextIds)
    syncMessengerFormToSelectedPageIds(nextIds)
  }

  const toggleMessengerPage = (pageId: string) => {
    const id = String(pageId)
    setSelectedMessengerPageIds((prev) => {
      const next = prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
      queueMicrotask(() => syncMessengerFormToSelectedPageIds(next))
      return next
    })
  }

  const handleCopyValue = async (value: string, successKey: string) => {
    if (!value)
      return
    try {
      await navigator.clipboard.writeText(value)
      toast.success(t(successKey as never, { ns: 'common' }))
    }
    catch {
      toast.error(t('settings.channelsCopyFailed', { ns: 'common' }))
    }
  }

  const handleDeleteChannel = async (channel: Channel) => {
    // eslint-disable-next-line no-alert
    const confirmed = window.confirm(
      t('settings.channelsDeleteConfirm', { ns: 'common', name: channel.name || channel.channel_id }),
    )
    if (!confirmed)
      return
    await deleteChannel(channel.channel_id)
    toast.success(t('api.actionSuccess', { ns: 'common' }))
    await loadChannels()
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-xl border border-components-panel-border bg-components-panel-bg px-4 py-3">
        <div className="mb-1 system-sm-semibold text-text-primary">{t('settings.channelsTitle', { ns: 'common' })}</div>
        <div className="mb-3 system-xs-regular text-text-tertiary">{t('settings.channelsDescription', { ns: 'common' })}</div>
        {!!providers.length && (
          <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-3">
            {providers.map((provider: ChannelProvider) => (
              <ProviderSummaryCard
                key={provider.channel_type}
                provider={provider}
                configuredCount={providerChannelCountMap[provider.channel_type] || 0}
                t={t}
                onAdd={openCreate}
              />
            ))}
          </div>
        )}
        <div className="mb-3 flex justify-end">
          <Button
            size="small"
            onClick={() => openCreate()}
          >
            {t('settings.channelsAdd', { ns: 'common' })}
          </Button>
        </div>
        {!channels.length && (
          <div className="system-xs-regular text-text-tertiary">{t('settings.channelsEmpty', { ns: 'common' })}</div>
        )}
        {!!channels.length && (
          <div className="space-y-2">
            {channels.map((channel: Channel) => (
              <ChannelItem
                key={channel.channel_id}
                channel={channel}
                t={t}
                onEdit={openEdit}
                onDelete={handleDeleteChannel}
              />
            ))}
          </div>
        )}
      </div>
      <Dialog
        open={isConfigModalOpen}
        onOpenChange={(open) => {
          if (!open)
            setIsConfigModalOpen(false)
        }}
      >
        <DialogContent className="w-[640px] max-w-[calc(100vw-2rem)] overflow-hidden p-0">
          <DialogCloseButton className="top-5 right-5" />
          <div className="border-b border-divider-subtle px-6 pt-6 pr-14 pb-4">
            <DialogTitle className="title-lg-semi-bold text-text-primary">
              {t('settings.channelsModalTitle', { ns: 'common' })}
            </DialogTitle>
          </div>
          <div className="max-h-[min(60dvh,calc(80dvh-8rem))] space-y-3 overflow-y-auto overscroll-contain px-6 py-4">
            {!isEditing && <SetupProgress setupStep={setupStep} t={t} />}
            {!isEditing && setupStep === 1 && (
              <SetupProviderSelector
                providers={providers}
                selectedChannelType={formValue.channel_type}
                t={t}
                onSelect={(provider: ChannelProvider) => {
                  setFormValue((prev: Channel) => ({
                    ...prev,
                    channel_type: provider.channel_type,
                    platform: provider.provider,
                    external_resource_id: provider.channel_type === 'zalo_personal' ? 'personal' : '',
                    oauth_application_id: '',
                    client_secret: '',
                    access_token: '',
                  }))
                  setOauthPages([])
                  setSelectedMessengerPageIds([])
                }}
              />
            )}
            {!isEditing && setupStep === 2 && isMessengerProvider && (
              <SetupSection>
                <div className="system-xs-semibold-uppercase text-text-tertiary">{t('settings.channelsAuthorizeMeta', { ns: 'common' })}</div>
                <FieldGroup
                  label={t('settings.channelsFacebookAppIdLabel', { ns: 'common' })}
                  hint={t('settings.channelsFacebookAppIdHint', { ns: 'common' })}
                >
                  <Input
                    value={messengerAuthAppId}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setMessengerAuthAppId(e.target.value)}
                    placeholder={t('settings.channelsPlaceholderFacebookAppId', { ns: 'common' })}
                  />
                </FieldGroup>
                <FieldGroup
                  label={t('settings.channelsFacebookAppSecretLabel', { ns: 'common' })}
                  hint={t('settings.channelsFacebookAppSecretHint', { ns: 'common' })}
                >
                  <Input
                    type="password"
                    value={messengerAuthAppSecret}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setMessengerAuthAppSecret(e.target.value)}
                    placeholder={t('settings.channelsPlaceholderFacebookAppSecret', { ns: 'common' })}
                  />
                </FieldGroup>
                <Button
                  variant="secondary"
                  onClick={handleConnectFacebook}
                  loading={isConnectingFacebook}
                  disabled={isConnectingFacebook}
                >
                  {t('settings.channelsConnectFacebookLoadPages', { ns: 'common' })}
                </Button>
                <FieldGroup
                  label={t('settings.channelsFacebookOAuthCallbackUrlLabel', { ns: 'common' })}
                  hint={t('settings.channelsFacebookOAuthCallbackUrlHint', { ns: 'common' })}
                >
                  <div className="flex items-center gap-2">
                    <Input disabled value={messengerOauthCallbackUrlPreview} onChange={() => {}} />
                    <Button
                      size="small"
                      variant="secondary"
                      onClick={() => handleCopyValue(messengerOauthCallbackUrlPreview, 'settings.channelsCopyOAuthCallbackUrlSuccess')}
                    >
                      {t('operation.copy', { ns: 'common' })}
                    </Button>
                  </div>
                </FieldGroup>
                {!!oauthPages.length && (
                  <FieldGroup
                    label={t('settings.channelsMessengerFacebookPagesLabel', { ns: 'common' })}
                    hint={t('settings.channelsMessengerFacebookPagesHint', { ns: 'common' })}
                  >
                    <div className="mb-2 flex flex-wrap gap-2">
                      <Button
                        size="small"
                        variant="secondary"
                        type="button"
                        onClick={() => applyMessengerPageSelection(oauthPages.map(p => String(p.id)))}
                      >
                        {t('settings.channelsMessengerSelectAllPages', { ns: 'common' })}
                      </Button>
                      <Button
                        size="small"
                        variant="secondary"
                        type="button"
                        onClick={() => applyMessengerPageSelection([])}
                      >
                        {t('settings.channelsMessengerClearPageSelection', { ns: 'common' })}
                      </Button>
                    </div>
                    <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-divider-subtle p-2">
                      {oauthPages.map(page => (
                        <label
                          key={String(page.id)}
                          className="flex cursor-pointer items-start gap-2 text-sm text-text-primary"
                        >
                          <input
                            type="checkbox"
                            className="mt-0.5"
                            checked={selectedMessengerPageIds.includes(String(page.id))}
                            onChange={() => toggleMessengerPage(String(page.id))}
                          />
                          <span>
                            {page.name || t('settings.channelsMessengerUnnamedPage', { ns: 'common' })}
                            {' '}
                            <span className="text-text-tertiary">
                              (
                              {page.id}
                              )
                            </span>
                          </span>
                        </label>
                      ))}
                    </div>
                  </FieldGroup>
                )}
              </SetupSection>
            )}
            {!isEditing && setupStep === 2 && !isMessengerProvider && isZaloPersonalProvider && (
              <SetupSection>
                <div className="system-sm-medium text-text-primary">
                  {t('settings.channelsZaloPersonalQrTitle', { ns: 'common' })}
                </div>
                <p className="system-xs-regular text-text-tertiary">
                  {t('settings.channelsZaloPersonalQrHint', { ns: 'common' })}
                </p>
                {zaloPersonalProvisioning && (
                  <p className="system-xs-regular text-text-tertiary">
                    {t('settings.channelsZaloPersonalDraftProvisioning', { ns: 'common' })}
                  </p>
                )}
                {!zaloPersonalProvisioning && (
                  <ZaloPersonalQrPanel
                    channelId={zaloPersonalDraftId}
                    active={!!zaloPersonalDraftId}
                    onConnected={() => setZaloPersonalQrConnected(true)}
                    t={t}
                  />
                )}
              </SetupSection>
            )}
            {!isEditing && setupStep === 2 && !isMessengerProvider && isZaloOaProvider && (
              <SetupSection>
                <div className="system-sm-medium text-text-primary">
                  {t('settings.channelsZaloQRTitle', { ns: 'common' })}
                </div>
                <p className="system-xs-regular text-text-tertiary">
                  {t('settings.channelsZaloOaStep2Hint', { ns: 'common' })}
                </p>
                <FieldGroup
                  label={t('settings.channelsZaloOAuthAppIdLabel', { ns: 'common' })}
                  hint={t('settings.channelsZaloOAuthAppIdHint', { ns: 'common' })}
                >
                  <Input
                    disabled={!!zaloOaDraftId}
                    value={formValue.oauth_application_id || ''}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, oauth_application_id: e.target.value }))}
                    placeholder={t('settings.channelsZaloOAuthAppIdLabel', { ns: 'common' })}
                  />
                </FieldGroup>
                <FieldGroup
                  label={t('settings.channelsFieldClientSecret', { ns: 'common' })}
                  hint={t('settings.channelsZaloAppSecretHint', { ns: 'common' })}
                >
                  <div className="flex items-center gap-2">
                    <Input
                      type={isClientSecretVisible ? 'text' : 'password'}
                      disabled={!!zaloOaDraftId}
                      value={formValue.client_secret || ''}
                      onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, client_secret: e.target.value }))}
                      placeholder={t('settings.channelsFieldClientSecret', { ns: 'common' })}
                    />
                    <Button
                      size="small"
                      variant="secondary"
                      disabled={!!zaloOaDraftId}
                      onClick={() => setIsClientSecretVisible(prev => !prev)}
                    >
                      {isClientSecretVisible ? <RiEyeOffLine className="size-4" /> : <RiEyeLine className="size-4" />}
                      <span className="ml-1">{isClientSecretVisible ? t('settings.channelsHideToken', { ns: 'common' }) : t('settings.channelsShowToken', { ns: 'common' })}</span>
                    </Button>
                  </div>
                </FieldGroup>
                {!zaloOaDraftId && (
                  <Button
                    variant="primary"
                    loading={zaloOaProvisioning}
                    disabled={zaloOaProvisioning}
                    onClick={() => { void handleStartZaloOaAuthorize() }}
                  >
                    {t('settings.channelsZaloOaAuthorizeButton', { ns: 'common' })}
                  </Button>
                )}
                {!!zaloOaDraftId && (
                  <ZaloOAuthPanel
                    channelId={zaloOaDraftId}
                    active={!!zaloOaDraftId}
                    onConnected={() => setZaloOaOAuthConnected(true)}
                    onStarted={meta => setZaloOaCallbackUrl(meta.oauth_callback_url)}
                    t={t}
                  />
                )}
              </SetupSection>
            )}
            {!isEditing && setupStep === 2 && !isMessengerProvider && !isZaloPersonalProvider && !isZaloOaProvider && (
              <SetupSection>
                {isMetaOAuthProvider && metaOAuthProvisioning && (
                  <div className="system-xs-regular text-text-tertiary">{t('settings.channelsOAuthDraftProvisioning', { ns: 'common' })}</div>
                )}
                <SetupManualHint isZalo={false} t={t} />
                {providerSetupConfig.requiresClientSecret && (
                  <FieldGroup
                    label={t('settings.channelsFieldClientSecret', { ns: 'common' })}
                    hint={t('settings.channelsGenericClientSecretHint', { ns: 'common' })}
                  >
                    <div className="flex items-center gap-2">
                      <Input
                        type={isClientSecretVisible ? 'text' : 'password'}
                        value={formValue.client_secret || ''}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, client_secret: e.target.value }))}
                        placeholder={t('settings.channelsFieldClientSecret', { ns: 'common' })}
                      />
                      <Button
                        size="small"
                        variant="secondary"
                        onClick={() => setIsClientSecretVisible(prev => !prev)}
                      >
                        {isClientSecretVisible ? <RiEyeOffLine className="size-4" /> : <RiEyeLine className="size-4" />}
                        <span className="ml-1">{isClientSecretVisible ? t('settings.channelsHideToken', { ns: 'common' }) : t('settings.channelsShowToken', { ns: 'common' })}</span>
                      </Button>
                    </div>
                  </FieldGroup>
                )}
                {providerSetupConfig.requiresAccessToken && (
                  <FieldGroup
                    label={t('settings.channelsFieldAccessToken', { ns: 'common' })}
                    hint={t('settings.channelsGenericAccessTokenHint', { ns: 'common' })}
                  >
                    <div className="flex items-center gap-2">
                      <Input
                        type={isAccessTokenVisible ? 'text' : 'password'}
                        value={formValue.access_token || ''}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, access_token: e.target.value }))}
                        placeholder={t('settings.channelsFieldAccessToken', { ns: 'common' })}
                      />
                      <Button
                        size="small"
                        variant="secondary"
                        onClick={() => setIsAccessTokenVisible(prev => !prev)}
                      >
                        {isAccessTokenVisible ? <RiEyeOffLine className="size-4" /> : <RiEyeLine className="size-4" />}
                        <span className="ml-1">{isAccessTokenVisible ? t('settings.channelsHideToken', { ns: 'common' }) : t('settings.channelsShowToken', { ns: 'common' })}</span>
                      </Button>
                    </div>
                  </FieldGroup>
                )}
                {providerSetupConfig.showApiVersion && (
                  <FieldGroup
                    label={t('settings.channelsFieldApiVersion', { ns: 'common' })}
                    hint={t('settings.channelsApiVersionHint', { ns: 'common' })}
                  >
                    <Input
                      value={formValue.api_version}
                      onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, api_version: e.target.value }))}
                      placeholder={t('settings.channelsFieldApiVersion', { ns: 'common' })}
                    />
                  </FieldGroup>
                )}
              </SetupSection>
            )}
            {!isEditing && setupStep === 2 && !!providerDocsUrl && (
              <Button
                variant="secondary"
                onClick={() => window.open(providerDocsUrl, '_blank', 'noopener,noreferrer')}
              >
                {t('settings.channelsOpenProviderDocs', { ns: 'common' })}
              </Button>
            )}
            {isFormStepVisible && (
              <>
                <FieldGroup label={t('settings.channelsProviderLabel', { ns: 'common' })}>
                  <PureSelect
                    disabled={isEditing}
                    value={formValue.channel_type}
                    options={providerOptions}
                    onChange={(value) => {
                      const provider = providers.find((item: ChannelProvider) => item.channel_type === value)
                      setFormValue((prev: Channel) => ({
                        ...prev,
                        channel_type: value,
                        platform: provider?.provider || prev.platform,
                      }))
                    }}
                    triggerProps={{ className: 'h-10 rounded-lg border border-components-input-border px-2' }}
                  />
                </FieldGroup>
                {usePerPageMessengerStudioApps
                  ? (
                      <div className="rounded-xl border border-components-panel-border bg-components-panel-bg p-3 shadow-sm">
                        <div className="mb-3">
                          <div className="system-sm-semibold text-text-primary">
                            {t('settings.channelsMessengerRouteTitle', { ns: 'common' })}
                          </div>
                          <div className="mt-1 system-xs-regular text-text-tertiary">
                            {t('settings.channelsMessengerPerPageTargetAppHint', { ns: 'common' })}
                          </div>
                        </div>
                        <div className="mb-4 flex flex-col gap-2 rounded-lg bg-background-default/80 px-3 py-2 sm:flex-row sm:items-center sm:gap-3">
                          <span className="system-2xs-semibold tracking-wide text-text-tertiary uppercase">
                            {t('settings.channelsMessengerQuickApplyLabel', { ns: 'common' })}
                          </span>
                          <div className="min-w-0 flex-1">
                            <PureSelect
                              value={messengerApplyAllDraft}
                              options={[{ value: '', label: t('settings.channelsSelectTargetApp', { ns: 'common' }) }, ...appOptionsForSelect]}
                              onChange={value => setMessengerApplyAllDraft(value)}
                              triggerProps={{ className: 'h-9 w-full rounded-lg border border-components-input-border px-2' }}
                            />
                          </div>
                          <Button
                            type="button"
                            variant="secondary"
                            className="h-9 shrink-0 px-3 whitespace-nowrap"
                            onClick={() => {
                              if (!messengerApplyAllDraft.trim()) {
                                toast.error(t('settings.channelsRequiredError', { ns: 'common' }))
                                return
                              }
                              setMessengerTargetAppByPageId((prev) => {
                                const next = { ...prev }
                                for (const id of selectedMessengerPageIds)
                                  next[id] = messengerApplyAllDraft
                                return next
                              })
                              toast.success(t('settings.channelsMessengerAppliedAppToAll', { ns: 'common' }))
                            }}
                          >
                            {t('settings.channelsMessengerApplyAppToAllButton', { ns: 'common' })}
                          </Button>
                        </div>
                        <div className="max-h-[min(360px,50vh)] divide-y divide-divider-subtle overflow-y-auto rounded-lg border border-divider-subtle">
                          {selectedMessengerPageIds.map(pid => (
                            <div
                              key={pid}
                              className="flex flex-col gap-2 px-3 py-3 sm:flex-row sm:items-center sm:gap-4"
                            >
                              <div className="min-w-0 flex-1">
                                <div className="system-sm-medium text-text-primary">
                                  {(oauthPages.find(p => String(p.id) === String(pid))?.name
                                    || t('settings.channelsMessengerUnnamedPage', { ns: 'common' }))}
                                </div>
                                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 system-2xs-regular text-text-tertiary">
                                  <span>
                                    ID
                                    {pid}
                                  </span>
                                  <span className="text-text-quaternary">┬╖</span>
                                  <span className="font-mono text-text-secondary">{`messenger-${pid}`}</span>
                                </div>
                              </div>
                              <div className="w-full sm:w-[min(100%,260px)] sm:shrink-0">
                                <PureSelect
                                  value={messengerTargetAppByPageId[pid] ?? ''}
                                  options={[{ value: '', label: t('settings.channelsSelectTargetApp', { ns: 'common' }) }, ...appOptionsForSelect]}
                                  onChange={value =>
                                    setMessengerTargetAppByPageId(prev => ({ ...prev, [pid]: value }))}
                                  triggerProps={{ className: 'h-10 w-full rounded-lg border border-components-input-border px-2' }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  : (
                      <FieldGroup
                        label={t('settings.channelsTargetAppLabel', { ns: 'common' })}
                        hint={t('settings.channelsTargetAppHint', { ns: 'common' })}
                      >
                        <PureSelect
                          value={formValue.app_id}
                          options={[{ value: '', label: t('settings.channelsSelectTargetApp', { ns: 'common' }) }, ...appOptionsForSelect]}
                          onChange={value => setFormValue((prev: Channel) => ({ ...prev, app_id: value }))}
                          triggerProps={{ className: 'h-10 rounded-lg border border-components-input-border px-2' }}
                        />
                      </FieldGroup>
                    )}
                {!isMessengerProvider && !isZaloPersonalDraftCreate && !isZaloOaDraftCreate && !isMetaOAuthDraftCreate && (
                  <FieldGroup
                    label={t('settings.channelsFieldChannelId', { ns: 'common' })}
                    hint={t('settings.channelsChannelIdHint', { ns: 'common' })}
                  >
                    <Input
                      disabled={isEditing}
                      value={formValue.channel_id}
                      onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, channel_id: e.target.value }))}
                      placeholder={t('settings.channelsFieldChannelId', { ns: 'common' })}
                    />
                  </FieldGroup>
                )}
                {isZaloPersonalDraftCreate && (
                  <FieldGroup
                    label={t('settings.channelsFieldChannelId', { ns: 'common' })}
                    hint={t('settings.channelsZaloPersonalChannelIdAutoHint', { ns: 'common' })}
                  >
                    <Input disabled value={formValue.channel_id} onChange={() => {}} />
                  </FieldGroup>
                )}
                {isMetaOAuthDraftCreate && (
                  <FieldGroup
                    label={t('settings.channelsFieldChannelId', { ns: 'common' })}
                    hint={t('settings.channelsOAuthChannelIdAutoHint', { ns: 'common' })}
                  >
                    <Input disabled value={formValue.channel_id} onChange={() => {}} />
                  </FieldGroup>
                )}
                {isZaloOaDraftCreate && (
                  <FieldGroup
                    label={t('settings.channelsFieldChannelId', { ns: 'common' })}
                    hint={t('settings.channelsZaloOaChannelIdAutoHint', { ns: 'common' })}
                  >
                    <Input disabled value={formValue.channel_id} onChange={() => {}} />
                  </FieldGroup>
                )}
                {isMessengerProvider && !usePerPageMessengerStudioApps && (
                  <FieldGroup
                    label={t('settings.channelsFieldChannelId', { ns: 'common' })}
                    hint={t('settings.channelsFieldChannelIdAuto', { ns: 'common' })}
                  >
                    <Input
                      disabled
                      value={formValue.channel_id}
                      onChange={() => {}}
                      placeholder={t('settings.channelsFieldChannelIdAuto', { ns: 'common' })}
                    />
                  </FieldGroup>
                )}
                {!(isMessengerProvider && usePerPageMessengerStudioApps) && (
                  <FieldGroup label={t('settings.channelsNameLabel', { ns: 'common' })}>
                    <Input
                      disabled={!isEditing && isMessengerProvider && selectedMessengerPageIds.length > 1}
                      value={formValue.name}
                      onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, name: e.target.value }))}
                      placeholder={t('settings.channelsFieldName', { ns: 'common' })}
                    />
                    {!isEditing && isMessengerProvider && selectedMessengerPageIds.length > 1 && (
                      <div className="system-xs-regular text-text-tertiary">{t('settings.channelsMessengerBulkNameHint', { ns: 'common' })}</div>
                    )}
                  </FieldGroup>
                )}
                {!(isMessengerProvider && usePerPageMessengerStudioApps) && !isZaloPersonalProvider && (
                  <FieldGroup
                    label={formValue.channel_type === 'facebook_messenger' ? t('settings.channelsFieldFacebookPageId', { ns: 'common' }) : t('settings.channelsFieldExternalResourceId', { ns: 'common' })}
                    hint={isMessengerProvider
                      ? t('settings.channelsFacebookPageIdHint', { ns: 'common' })
                      : providerSetupConfig.resourceHintKey
                        ? t(providerSetupConfig.resourceHintKey as never, { ns: 'common' })
                        : undefined}
                  >
                    <Input
                      disabled={isMessengerProvider && !!oauthPages.length}
                      value={formValue.external_resource_id}
                      onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, external_resource_id: e.target.value }))}
                      placeholder={formValue.channel_type === 'facebook_messenger' ? t('settings.channelsFieldFacebookPageId', { ns: 'common' }) : t('settings.channelsFieldExternalResourceId', { ns: 'common' })}
                    />
                  </FieldGroup>
                )}
                {!isZaloPersonalProvider && (
                  <FieldGroup
                    label={t('settings.channelsVerifyTokenLabel', { ns: 'common' })}
                    hint={t('settings.channelsVerifyTokenHint', { ns: 'common' })}
                  >
                    <div className="flex items-center gap-2">
                      <Input
                        type={isVerifyTokenVisible ? 'text' : 'password'}
                        value={formValue.verify_token || ''}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, verify_token: e.target.value }))}
                        placeholder={isEditing
                          ? t('settings.channelsEditVerifyTokenPlaceholder', { ns: 'common' })
                          : t('settings.channelsFieldVerifyTokenAuto', { ns: 'common' })}
                      />
                      <Button
                        size="small"
                        variant="secondary"
                        onClick={() => setIsVerifyTokenVisible(prev => !prev)}
                      >
                        {isVerifyTokenVisible ? <RiEyeOffLine className="size-4" /> : <RiEyeLine className="size-4" />}
                        <span className="ml-1">{isVerifyTokenVisible ? t('settings.channelsHideToken', { ns: 'common' }) : t('settings.channelsShowToken', { ns: 'common' })}</span>
                      </Button>
                    </div>
                  </FieldGroup>
                )}
                {isMessengerProvider && (
                  <SetupSection>
                    <div className="rounded-lg border border-divider-subtle bg-background-default px-3 py-2">
                      <div className="mb-2 system-xs-semibold-uppercase text-text-tertiary">{t('settings.channelsMetaWebhookSetupTitle', { ns: 'common' })}</div>
                      <FieldGroup
                        label={t('settings.channelsWebhookUrlLabel', { ns: 'common' })}
                        hint={t('settings.channelsWebhookUrlHint', { ns: 'common' })}
                      >
                        {usePerPageMessengerStudioApps
                          ? (
                              <div className="max-h-52 space-y-2 overflow-y-auto">
                                <div className="system-2xs-regular text-text-tertiary">
                                  {t('settings.channelsMessengerBulkWebhookHint', { ns: 'common' })}
                                </div>
                                {selectedMessengerPageIds.map(pid => (
                                  <div key={pid} className="flex min-w-0 items-center gap-2">
                                    <Input
                                      className="min-w-0 shrink"
                                      disabled
                                      value={buildMessengerWebhookUrlForPageId(pid)}
                                      onChange={() => {}}
                                    />
                                    <Button
                                      size="small"
                                      variant="secondary"
                                      className="shrink-0"
                                      onClick={() =>
                                        handleCopyValue(buildMessengerWebhookUrlForPageId(pid), 'settings.channelsCopyWebhookUrlSuccess')}
                                    >
                                      {t('operation.copy', { ns: 'common' })}
                                    </Button>
                                  </div>
                                ))}
                              </div>
                            )
                          : (
                              <div className="flex items-center gap-2">
                                <Input disabled value={webhookUrlPreview} onChange={() => {}} />
                                <Button size="small" variant="secondary" onClick={() => handleCopyValue(webhookUrlPreview, 'settings.channelsCopyWebhookUrlSuccess')}>
                                  {t('operation.copy', { ns: 'common' })}
                                </Button>
                              </div>
                            )}
                      </FieldGroup>
                      <FieldGroup
                        label={t('settings.channelsWebhookVerifyTokenLabel', { ns: 'common' })}
                        hint={t('settings.channelsWebhookVerifyTokenHint', { ns: 'common' })}
                      >
                        <div className="flex items-center gap-2">
                          <Input disabled value={formValue.verify_token || ''} onChange={() => {}} />
                          <Button size="small" variant="secondary" onClick={() => handleCopyValue(formValue.verify_token || '', 'settings.channelsCopyVerifyTokenSuccess')}>
                            {t('operation.copy', { ns: 'common' })}
                          </Button>
                        </div>
                      </FieldGroup>
                      <FieldGroup
                        label={t('settings.channelsFacebookOAuthCallbackUrlLabel', { ns: 'common' })}
                        hint={t('settings.channelsFacebookOAuthCallbackUrlHint', { ns: 'common' })}
                      >
                        <div className="flex items-center gap-2">
                          <Input disabled value={messengerOauthCallbackUrlPreview} onChange={() => {}} />
                          <Button
                            size="small"
                            variant="secondary"
                            onClick={() => handleCopyValue(messengerOauthCallbackUrlPreview, 'settings.channelsCopyOAuthCallbackUrlSuccess')}
                          >
                            {t('operation.copy', { ns: 'common' })}
                          </Button>
                        </div>
                      </FieldGroup>
                      <div className="system-xs-regular text-text-secondary">
                        {t('settings.channelsMetaWebhookFieldsHint', { ns: 'common' })}
                      </div>
                    </div>
                  </SetupSection>
                )}
                {isZaloOaProvider && (
                  <SetupSection>
                    <div className="rounded-lg border border-divider-subtle bg-background-default px-3 py-2">
                      <div className="mb-2 system-xs-semibold-uppercase text-text-tertiary">{t('settings.channelsZaloWebhookSetupTitle', { ns: 'common' })}</div>
                      <FieldGroup
                        label={t('settings.channelsWebhookUrlLabel', { ns: 'common' })}
                        hint={t('settings.channelsZaloWebhookUrlHint', { ns: 'common' })}
                      >
                        <div className="flex items-center gap-2">
                          <Input disabled value={webhookUrlPreview} onChange={() => {}} />
                          <Button size="small" variant="secondary" onClick={() => handleCopyValue(webhookUrlPreview, 'settings.channelsCopyWebhookUrlSuccess')}>
                            {t('operation.copy', { ns: 'common' })}
                          </Button>
                        </div>
                      </FieldGroup>
                      {(editingChannel?.oauth_callback_url || zaloOaCallbackUrl).length > 0 && (
                        <FieldGroup
                          label={t('settings.channelsZaloCallbackUrlLabel', { ns: 'common' })}
                          hint={t('settings.channelsZaloCallbackUrlHint', { ns: 'common' })}
                        >
                          <div className="flex items-center gap-2">
                            <Input disabled value={editingChannel?.oauth_callback_url || zaloOaCallbackUrl} onChange={() => {}} />
                            <Button size="small" variant="secondary" onClick={() => handleCopyValue(editingChannel?.oauth_callback_url || zaloOaCallbackUrl, 'settings.channelsCopyWebhookUrlSuccess')}>
                              {t('operation.copy', { ns: 'common' })}
                            </Button>
                          </div>
                        </FieldGroup>
                      )}
                      <div className="system-xs-regular text-text-secondary">
                        {t('settings.channelsZaloWebhookFieldsHint', { ns: 'common' })}
                      </div>
                    </div>
                  </SetupSection>
                )}
                {!isEditing && isZaloPersonalProvider && (
                  <div className="rounded-lg border border-divider-subtle bg-state-base-hover px-3 py-2 text-xs leading-relaxed text-text-secondary">
                    {isZaloPersonalDraftCreate
                      ? t('settings.channelsZaloPersonalStep3FinalizeHint', { ns: 'common' })
                      : t('settings.channelsZaloPersonalStep3Hint', { ns: 'common' })}
                  </div>
                )}
                {!isEditing && isZaloOaProvider && (
                  <div className="rounded-lg border border-divider-subtle bg-state-base-hover px-3 py-2 text-xs leading-relaxed text-text-secondary">
                    {isZaloOaDraftCreate
                      ? t('settings.channelsZaloOaStep3FinalizeHint', { ns: 'common' })
                      : t('settings.channelsZaloOaStep3Hint', { ns: 'common' })}
                  </div>
                )}
                {!isMessengerProvider && isEditing && (
                  <>
                    {isZaloOaProvider && (
                      <FieldGroup
                        label={t('settings.channelsZaloOAuthAppIdLabel', { ns: 'common' })}
                        hint={t('settings.channelsZaloOAuthAppIdHint', { ns: 'common' })}
                      >
                        <Input
                          value={formValue.oauth_application_id || ''}
                          onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, oauth_application_id: e.target.value }))}
                          placeholder={t('settings.channelsZaloOAuthAppIdLabel', { ns: 'common' })}
                        />
                      </FieldGroup>
                    )}
                    <FieldGroup
                      label={t('settings.channelsFieldClientSecret', { ns: 'common' })}
                      hint={editClientSecretHint}
                    >
                      <div className="flex items-center gap-2">
                        <Input
                          type={isClientSecretVisible ? 'text' : 'password'}
                          value={formValue.client_secret || ''}
                          onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, client_secret: e.target.value }))}
                          placeholder={maskedSecrets.client_secret || t('settings.channelsFieldClientSecretOptional', { ns: 'common' })}
                        />
                        <Button
                          size="small"
                          variant="secondary"
                          onClick={() => setIsClientSecretVisible(prev => !prev)}
                        >
                          {isClientSecretVisible ? <RiEyeOffLine className="size-4" /> : <RiEyeLine className="size-4" />}
                          <span className="ml-1">{isClientSecretVisible ? t('settings.channelsHideToken', { ns: 'common' }) : t('settings.channelsShowToken', { ns: 'common' })}</span>
                        </Button>
                      </div>
                    </FieldGroup>
                    {!isZaloOaProvider && !isZaloPersonalProvider && (
                      <FieldGroup
                        label={t('settings.channelsFieldAccessToken', { ns: 'common' })}
                        hint={editAccessTokenHint}
                      >
                        <div className="flex items-center gap-2">
                          <Input
                            type={isAccessTokenVisible ? 'text' : 'password'}
                            value={formValue.access_token || ''}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, access_token: e.target.value }))}
                            placeholder={maskedSecrets.access_token || t('settings.channelsFieldAccessTokenOptional', { ns: 'common' })}
                          />
                          <Button
                            size="small"
                            variant="secondary"
                            onClick={() => setIsAccessTokenVisible(prev => !prev)}
                          >
                            {isAccessTokenVisible ? <RiEyeOffLine className="size-4" /> : <RiEyeLine className="size-4" />}
                            <span className="ml-1">{isAccessTokenVisible ? t('settings.channelsHideToken', { ns: 'common' }) : t('settings.channelsShowToken', { ns: 'common' })}</span>
                          </Button>
                        </div>
                      </FieldGroup>
                    )}
                    {providerSetupConfig.showApiVersion && (
                      <FieldGroup
                        label={t('settings.channelsFieldApiVersion', { ns: 'common' })}
                        hint={t('settings.channelsApiVersionHint', { ns: 'common' })}
                      >
                        <Input
                          value={formValue.api_version}
                          onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, api_version: e.target.value }))}
                          placeholder={t('settings.channelsFieldApiVersion', { ns: 'common' })}
                        />
                      </FieldGroup>
                    )}
                  </>
                )}
                {isZaloOaProvider && (
                  <>
                    <label className="flex items-center gap-2 text-sm text-text-secondary">
                      <input
                        type="checkbox"
                        checked={!!formValue.zalo_auto_reply_enabled}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, zalo_auto_reply_enabled: e.target.checked }))}
                      />
                      {t('settings.channelsZaloAutoReplyLabel', { ns: 'common' })}
                    </label>
                    <label className="flex items-center gap-2 text-sm text-text-secondary">
                      <input
                        type="checkbox"
                        checked={!!formValue.zalo_info_card_enabled}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, zalo_info_card_enabled: e.target.checked }))}
                      />
                      {t('settings.channelsZaloInfoCardLabel', { ns: 'common' })}
                    </label>
                    {!!formValue.zalo_info_card_enabled && (
                      <div className="space-y-2 rounded-lg border border-divider-subtle p-3">
                        <FieldGroup label={t('settings.channelsZaloInfoCardTitle', { ns: 'common' })}>
                          <Input
                            value={formValue.zalo_info_card_title || ''}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, zalo_info_card_title: e.target.value }))}
                          />
                        </FieldGroup>
                        <FieldGroup label={t('settings.channelsZaloInfoCardSubtitle', { ns: 'common' })}>
                          <Input
                            value={formValue.zalo_info_card_subtitle || ''}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, zalo_info_card_subtitle: e.target.value }))}
                          />
                        </FieldGroup>
                        <FieldGroup label={t('settings.channelsZaloInfoCardImageUrl', { ns: 'common' })}>
                          <Input
                            value={formValue.zalo_info_card_image_url || ''}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, zalo_info_card_image_url: e.target.value }))}
                            placeholder="https://"
                          />
                        </FieldGroup>
                      </div>
                    )}
                  </>
                )}
                <label className="flex items-center gap-2 text-sm text-text-secondary">
                  <input
                    type="checkbox"
                    checked={formValue.enabled}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, enabled: e.target.checked }))}
                  />
                  {t('settings.channelsEnabledLabel', { ns: 'common' })}
                </label>
                {isEditing && isZaloOaProvider && editingChannel && (
                  <Button
                    variant="secondary"
                    className="w-full"
                    onClick={() => {
                      setZaloOAuthChannelId(editingChannel.channel_id)
                      setZaloOAuthOpen(true)
                    }}
                  >
                    {(editingChannel.oauth_status === 'pending_auth' || editingChannel.oauth_status === 'expired')
                      ? t('settings.channelsZaloReconnectButton', { ns: 'common' })
                      : t('settings.channelsZaloConnectButton', { ns: 'common' })}
                  </Button>
                )}
                {isEditing && isZaloPersonalProvider && editingChannel && (
                  <Button
                    variant="secondary"
                    className="w-full"
                    onClick={() => {
                      setZaloPersonalChannelId(editingChannel.channel_id)
                      setZaloPersonalOpen(true)
                    }}
                  >
                    {editingChannel.personal_login_status === 'connected'
                      ? t('settings.channelsZaloPersonalReconnectButton', { ns: 'common' })
                      : t('settings.channelsZaloPersonalConnectButton', { ns: 'common' })}
                  </Button>
                )}
              </>
            )}
          </div>
          {(isFormStepVisible || (!isEditing && setupStep < 3)) && (
            <div className="border-t border-divider-subtle px-6 py-4">
              {isFormStepVisible && (
                <div className="flex justify-end gap-2">
                  <Button onClick={() => setIsConfigModalOpen(false)}>{t('operation.cancel', { ns: 'common' })}</Button>
                  <Button variant="primary" loading={isSavingChannel} disabled={isSavingChannel} onClick={saveChannel}>{t('operation.save', { ns: 'common' })}</Button>
                </div>
              )}
              {!isEditing && setupStep < 3 && (
                <SetupNavigation
                  setupStep={setupStep}
                  canGoNext={!((setupStep === 1 && !canGoStep2) || (setupStep === 2 && !canGoStep3))}
                  onBack={() => setSetupStep((prev: SetupStep) => {
                    if (prev === 3 && (isZaloPersonalProvider || isZaloOaProvider))
                      return 2
                    if (prev > 1)
                      return (prev - 1) as SetupStep
                    return prev
                  })}
                  onNext={() => {
                    if (setupStep === 1 && canGoStep2)
                      setSetupStep(2)
                    else if (setupStep === 2 && canGoStep3)
                      setSetupStep(3)
                  }}
                  t={t}
                />
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
      <ZaloOAuthModal
        channelId={zaloOAuthChannelId}
        open={zaloOAuthOpen}
        onClose={() => {
          setZaloOAuthOpen(false)
          setZaloOAuthChannelId(null)
        }}
        onConnected={loadChannels}
        t={t}
      />
      <ZaloPersonalQrModal
        channelId={zaloPersonalChannelId}
        open={zaloPersonalOpen}
        onClose={() => {
          setZaloPersonalOpen(false)
          setZaloPersonalChannelId(null)
        }}
        onConnected={loadChannels}
        t={t}
      />
    </div>
  )
}

export default ChannelsPage
