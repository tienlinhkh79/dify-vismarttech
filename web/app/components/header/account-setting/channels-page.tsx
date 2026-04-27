'use client'
import type { Channel, ChannelProvider } from '@/service/tools'
import type { ChangeEvent } from 'react'
import type { App } from '@/types/app'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Button from '@/app/components/base/button'
import Drawer from '@/app/components/base/drawer-plus'
import Input from '@/app/components/base/input'
import { toast } from '@/app/components/base/ui/toast'
import { openOAuthPopup } from '@/hooks/use-oauth'
import { useAppList } from '@/service/use-apps'
import {
  createChannel,
  getMessengerOAuthAuthorizationUrl,
  listChannelProviders,
  listChannels,
  updateChannel,
} from '@/service/tools'

const ChannelsPage = () => {
  const MESSENGER_OAUTH_APP_ID_STORAGE_KEY = 'dify_messenger_oauth_app_id'
  const { t } = useTranslation()
  const [providers, setProviders] = useState<ChannelProvider[]>([])
  const [channels, setChannels] = useState<Channel[]>([])
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [editingChannelId, setEditingChannelId] = useState<string | null>(null)
  const [isConnectingFacebook, setIsConnectingFacebook] = useState(false)
  const [oauthPages, setOauthPages] = useState<Array<{ id: string, name: string, access_token: string }>>([])
  const [messengerAuthAppId, setMessengerAuthAppId] = useState('')
  const [messengerAuthAppSecret, setMessengerAuthAppSecret] = useState('')
  const [maskedSecrets, setMaskedSecrets] = useState<{
    verify_token?: string
    client_secret?: string
    access_token?: string
  }>({})
  const [formValue, setFormValue] = useState<Channel>({
    channel_type: 'facebook_messenger',
    channel_id: '',
    app_id: '',
    name: '',
    external_resource_id: '',
    verify_token: '',
    client_secret: '',
    access_token: '',
    api_version: 'v23.0',
    enabled: true,
    platform: 'messenger',
  })
  const { data: appListRes } = useAppList({ page: 1, limit: 100, mode: 'all' }, { enabled: true })
  const appOptions = appListRes?.data || []

  const generateVerifyToken = () => `vk_${Math.random().toString(36).slice(2, 12)}`

  const loadChannels = async () => {
    try {
      const [channelsRes, providersRes] = await Promise.all([listChannels(), listChannelProviders()])
      setProviders(providersRes.data || [])
      setChannels(channelsRes.data || [])
    }
    catch {
      setProviders([])
      setChannels([])
    }
  }

  useEffect(() => {
    loadChannels()
    if (typeof window !== 'undefined') {
      const savedAppId = window.localStorage.getItem(MESSENGER_OAUTH_APP_ID_STORAGE_KEY) || ''
      setMessengerAuthAppId(savedAppId)
    }
  }, [])

  const openCreate = () => {
    setEditingChannelId(null)
    setFormValue({
      channel_type: 'facebook_messenger',
      channel_id: '',
      app_id: '',
      name: '',
      external_resource_id: '',
      verify_token: generateVerifyToken(),
      client_secret: '',
      access_token: '',
      api_version: 'v23.0',
      enabled: true,
      platform: 'messenger',
    })
    setOauthPages([])
    if (typeof window !== 'undefined') {
      setMessengerAuthAppId(window.localStorage.getItem(MESSENGER_OAUTH_APP_ID_STORAGE_KEY) || '')
    }
    else {
      setMessengerAuthAppId('')
    }
    setMessengerAuthAppSecret('')
    setMaskedSecrets({})
    setIsDrawerOpen(true)
  }

  const openEdit = (channel: Channel) => {
    setEditingChannelId(channel.channel_id)
    setFormValue({
      ...channel,
      verify_token: '',
      client_secret: '',
      access_token: '',
    })
    setOauthPages(channel.external_resource_id ? [{
      id: channel.external_resource_id,
      name: channel.name || channel.channel_id,
      access_token: '',
    }] : [])
    if (typeof window !== 'undefined') {
      setMessengerAuthAppId(window.localStorage.getItem(MESSENGER_OAUTH_APP_ID_STORAGE_KEY) || '')
    }
    else {
      setMessengerAuthAppId('')
    }
    setMessengerAuthAppSecret('')
    setMaskedSecrets({
      verify_token: channel.verify_token_masked,
      client_secret: channel.client_secret_masked,
      access_token: channel.access_token_masked,
    })
    setIsDrawerOpen(true)
  }

  const selectedProvider = providers.find((item: ChannelProvider) => item.channel_type === formValue.channel_type)
  const isEditing = !!editingChannelId
  const isComingSoonProvider = selectedProvider?.status === 'coming_soon'
  const isMessengerProvider = formValue.channel_type === 'facebook_messenger'
  const providerChannelCountMap = channels.reduce<Record<string, number>>((acc: Record<string, number>, channel: Channel) => {
    acc[channel.channel_type] = (acc[channel.channel_type] || 0) + 1
    return acc
  }, {})

  const saveChannel = async () => {
    if (!formValue.channel_id.trim() || !formValue.name.trim() || !formValue.app_id.trim() || !formValue.external_resource_id.trim()) {
      toast.error(t('settings.channelsRequiredError', { ns: 'common' }))
      return
    }
    if (!isEditing && (!formValue.verify_token?.trim() || !formValue.client_secret?.trim() || !formValue.access_token?.trim())) {
      toast.error(t('settings.channelsSecretRequiredError', { ns: 'common' }))
      return
    }
    if (isComingSoonProvider) {
      toast.error(t('settings.channelsComingSoonError', { ns: 'common' }))
      return
    }
    const payload: Partial<Channel> = {
      channel_type: formValue.channel_type,
      channel_id: formValue.channel_id.trim(),
      app_id: formValue.app_id.trim(),
      name: formValue.name.trim(),
      external_resource_id: formValue.external_resource_id.trim(),
      api_version: formValue.api_version.trim() || 'v23.0',
      enabled: formValue.enabled,
    }
    if (formValue.verify_token?.trim())
      payload.verify_token = formValue.verify_token.trim()
    if (formValue.client_secret?.trim())
      payload.client_secret = formValue.client_secret.trim()
    if (formValue.access_token?.trim())
      payload.access_token = formValue.access_token.trim()
    if (formValue.platform)
      payload.platform = formValue.platform

    if (isEditing)
      await updateChannel(editingChannelId!, payload)
    else
      await createChannel(payload as Channel)

    toast.success(t('api.actionSuccess', { ns: 'common' }))
    setIsDrawerOpen(false)
    await loadChannels()
  }

  const handleConnectFacebook = async () => {
    setIsConnectingFacebook(true)
    try {
      const messengerAppId = messengerAuthAppId.trim()
      const messengerAppSecret = messengerAuthAppSecret.trim()
      const graphApiVersion = String(formValue.api_version || 'v23.0').trim() || 'v23.0'
      if (!messengerAppId || !messengerAppSecret) {
        toast.error('Please enter Facebook App ID and App Secret first.')
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
        toast.error('Failed to start Facebook authorization.')
        return
      }
      openOAuthPopup(res.authorization_url, (data) => {
        if (!data?.success) {
          toast.error(data?.errorDescription || 'Facebook authorization failed.')
          return
        }
        const pages = data?.messenger_oauth?.pages || []
        if (!pages.length) {
          toast.error('No Facebook pages found for this account.')
          return
        }
        setOauthPages(pages)
        const firstPage = pages[0]
        setFormValue((prev: Channel) => ({
          ...prev,
          external_resource_id: String(firstPage.id),
          access_token: String(firstPage.access_token),
          api_version: data?.messenger_oauth?.graph_api_version || graphApiVersion,
        }))
        toast.success('Facebook connected. Page list loaded.')
      })
    }
    finally {
      setIsConnectingFacebook(false)
    }
  }

  const handleSelectFacebookPage = (pageId: string) => {
    const selected = oauthPages.find((page: { id: string, name: string, access_token: string }) => page.id === pageId)
    if (!selected)
      return
    setFormValue((prev: Channel) => ({
      ...prev,
      channel_id: isEditing ? prev.channel_id : `messenger-${selected.id}`,
      name: isEditing ? prev.name : (selected.name || prev.name),
      external_resource_id: selected.id,
      access_token: selected.access_token,
    }))
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-xl border border-components-panel-border bg-components-panel-bg px-4 py-3">
        <div className="mb-1 system-sm-semibold text-text-primary">{t('settings.channelsTitle', { ns: 'common' })}</div>
        <div className="mb-3 system-xs-regular text-text-tertiary">{t('settings.channelsDescription', { ns: 'common' })}</div>
        {!!providers.length && (
          <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-3">
            {providers.map((provider: ChannelProvider) => {
              const configuredCount = providerChannelCountMap[provider.channel_type] || 0
              const isComingSoon = provider.status === 'coming_soon'
              return (
                <div
                  key={provider.channel_type}
                  className="rounded-lg border border-divider-subtle px-3 py-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="system-sm-medium text-text-primary">{provider.display_name}</div>
                    <div className={`rounded px-1.5 py-0.5 text-[10px] ${isComingSoon ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>
                      {isComingSoon ? 'Coming soon' : 'Active'}
                    </div>
                  </div>
                  <div className="mt-1 system-xs-regular text-text-tertiary">
                    {configuredCount} configured channel{configuredCount === 1 ? '' : 's'}
                  </div>
                </div>
              )
            })}
          </div>
        )}
        <div className="mb-3 flex justify-end">
          <Button
            size="small"
            onClick={openCreate}
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
              <div
                key={channel.channel_id}
                className="flex items-center justify-between rounded-lg border border-divider-subtle px-3 py-2"
              >
                <div>
                  <div className="system-sm-medium text-text-primary">{channel.name || channel.channel_id}</div>
                  <div className="mt-0.5 system-xs-regular text-text-tertiary">
                    {channel.platform} · {channel.channel_id} · {channel.enabled ? t('dataSource.website.active', { ns: 'common' }) : t('dataSource.website.inactive', { ns: 'common' })}
                  </div>
                </div>
                <Button
                  size="small"
                  variant="secondary"
                  onClick={() => openEdit(channel)}
                >
                  {t('operation.edit', { ns: 'common' })}
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
      {isDrawerOpen && (
        <Drawer
          isShow
          onHide={() => setIsDrawerOpen(false)}
          dialogClassName="z-[1200]"
          title={t('settings.channelsModalTitle', { ns: 'common' })}
          panelClassName="mt-[64px] mb-2 w-[420px]! border-components-panel-border"
          maxWidthClassName="max-w-[420px]!"
          height="calc(100vh - 64px)"
          contentClassName="bg-components-panel-bg!"
          body={(
            <div className="space-y-3 px-6 py-4">
              <select
                className="w-full rounded-lg border border-components-input-border bg-components-input-bg-normal px-2 py-2 text-text-primary"
                disabled={isEditing}
                value={formValue.channel_type}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                  const provider = providers.find((item: ChannelProvider) => item.channel_type === e.target.value)
                  setFormValue((prev: Channel) => ({
                    ...prev,
                    channel_type: e.target.value,
                    platform: provider?.provider || prev.platform,
                  }))
                }}
              >
                {providers.map((provider: ChannelProvider) => (
                  <option key={provider.channel_type} value={provider.channel_type}>
                    {provider.display_name}
                    {provider.status === 'coming_soon' ? ' (Coming soon)' : ''}
                  </option>
                ))}
              </select>
              {!isMessengerProvider && (
                <Input
                  disabled={isEditing}
                  value={formValue.channel_id}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, channel_id: e.target.value }))}
                  placeholder="channel_id"
                />
              )}
              {isMessengerProvider && (
                <Input
                  disabled
                  value={formValue.channel_id}
                  onChange={() => {}}
                  placeholder="channel_id (auto-generated after selecting page)"
                />
              )}
              <Input
                value={formValue.name}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, name: e.target.value }))}
                placeholder="channel name"
              />
              <select
                className="w-full rounded-lg border border-components-input-border bg-components-input-bg-normal px-2 py-2 text-text-primary"
                value={formValue.app_id}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFormValue((prev: Channel) => ({ ...prev, app_id: e.target.value }))}
              >
                <option value="">Select target app</option>
                {appOptions.map((app: App) => (
                  <option key={app.id} value={app.id}>{app.name}</option>
                ))}
              </select>
              {isMessengerProvider && (
                <>
                  <Input
                    value={messengerAuthAppId}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setMessengerAuthAppId(e.target.value)}
                    placeholder="facebook_app_id"
                  />
                  <Input
                    type="password"
                    value={messengerAuthAppSecret}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setMessengerAuthAppSecret(e.target.value)}
                    placeholder="facebook_app_secret"
                  />
                  <Button
                    variant="secondary"
                    onClick={handleConnectFacebook}
                    loading={isConnectingFacebook}
                    disabled={isConnectingFacebook}
                  >
                    Connect Facebook and Load Pages
                  </Button>
                  {!!oauthPages.length && (
                    <select
                      className="w-full rounded-lg border border-components-input-border bg-components-input-bg-normal px-2 py-2 text-text-primary"
                      value={formValue.external_resource_id}
                      onChange={(e: ChangeEvent<HTMLSelectElement>) => handleSelectFacebookPage(e.target.value)}
                    >
                      {oauthPages.map(page => (
                        <option key={page.id} value={page.id}>
                          {page.name} ({page.id})
                        </option>
                      ))}
                    </select>
                  )}
                </>
              )}
              <Input
                value={formValue.external_resource_id}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, external_resource_id: e.target.value }))}
                placeholder={formValue.channel_type === 'facebook_messenger' ? 'facebook_page_id' : 'external_resource_id'}
              />
              <Input
                value={formValue.verify_token || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, verify_token: e.target.value }))}
                placeholder={isEditing
                  ? (maskedSecrets.verify_token || 'verify_token (optional to keep current)')
                  : 'verify_token (auto-generated or custom)'}
              />
              <Input
                type="password"
                value={formValue.client_secret || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, client_secret: e.target.value }))}
                placeholder={isEditing
                  ? (maskedSecrets.client_secret || 'client_secret (optional to keep current)')
                  : 'client_secret'}
              />
              <Input
                type="password"
                value={formValue.access_token || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, access_token: e.target.value }))}
                placeholder={isEditing
                  ? (maskedSecrets.access_token || 'access_token (optional to keep current)')
                  : 'access_token'}
              />
              <Input
                value={formValue.api_version}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, api_version: e.target.value }))}
                placeholder="api version"
              />
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={formValue.enabled}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setFormValue((prev: Channel) => ({ ...prev, enabled: e.target.checked }))}
                />
                {t('settings.channelsEnabledLabel', { ns: 'common' })}
              </label>
              {isComingSoonProvider && (
                <div className="rounded-lg bg-background-default p-2 text-xs text-text-tertiary">
                  {t('settings.channelsComingSoonWarning', { ns: 'common' })}
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <Button onClick={() => setIsDrawerOpen(false)}>{t('operation.cancel', { ns: 'common' })}</Button>
                <Button variant="primary" onClick={saveChannel}>{t('operation.save', { ns: 'common' })}</Button>
              </div>
            </div>
          )}
        />
      )}
    </div>
  )
}

export default ChannelsPage
