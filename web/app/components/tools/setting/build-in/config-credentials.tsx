'use client'
import type { FC } from 'react'
import type { Collection } from '../../types'
import { noop } from 'es-toolkit/function'
import * as React from 'react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Button from '@/app/components/base/button'
import Drawer from '@/app/components/base/drawer-plus'
import { LinkExternal02 } from '@/app/components/base/icons/src/vender/line/general'
import Loading from '@/app/components/base/loading'
import { toast } from '@/app/components/base/ui/toast'
import { useLanguage } from '@/app/components/header/account-setting/model-provider-page/hooks'
import Form from '@/app/components/header/account-setting/model-provider-page/model-modal/Form'
import { openOAuthPopup } from '@/hooks/use-oauth'
import {
  createMessengerChannel,
  fetchBuiltInToolCredential,
  fetchBuiltInToolCredentialSchema,
  getMessengerOAuthAuthorizationUrl,
  listMessengerChannels,
  updateMessengerChannel,
} from '@/service/tools'
import { cn } from '@/utils/classnames'
import { addDefaultValue, toolCredentialToFormSchemas } from '../../utils/to-form-schema'

type Props = {
  collection: Collection
  onCancel: () => void
  onSaved: (value: Record<string, any>) => void
  initialMessengerChannelId?: string
  onMessengerChannelsUpdated?: () => void | Promise<void>
  isHideRemoveBtn?: boolean
  onRemove?: () => void
  isSaving?: boolean
}

type MessengerOAuthPage = {
  id: string
  name: string
  access_token: string
}

const ConfigCredential: FC<Props> = ({
  collection,
  onCancel,
  onSaved,
  initialMessengerChannelId,
  onMessengerChannelsUpdated,
  isHideRemoveBtn,
  onRemove = noop,
  isSaving,
}) => {
  const { t } = useTranslation()
  const language = useLanguage()
  const [credentialSchema, setCredentialSchema] = useState<any>(null)
  const { name: collectionName } = collection
  const [tempCredential, setTempCredential] = React.useState<any>({})
  const [isLoading, setIsLoading] = React.useState(false)
  const [oauthPages, setOauthPages] = React.useState<MessengerOAuthPage[]>([])
  const [channelIdInput, setChannelIdInput] = React.useState('')
  const [channelNameInput, setChannelNameInput] = React.useState('Messenger Main Channel')
  const [channelAppIdInput, setChannelAppIdInput] = React.useState('')
  const [channelVerifyTokenInput, setChannelVerifyTokenInput] = React.useState('')
  const [channelEnabledInput, setChannelEnabledInput] = React.useState(true)
  const [isSavingChannel, setIsSavingChannel] = React.useState(false)
  const [existingChannelIds, setExistingChannelIds] = React.useState<string[]>([])
  const isMessenger = collectionName === 'messenger' || collectionName.endsWith('/messenger')

  const callbackUrl = channelIdInput
    ? `${globalThis.location.origin}/api/triggers/messenger/webhook/${channelIdInput}`
    : ''

  useEffect(() => {
    let cancelled = false

    const loadCredential = async () => {
      // Reset local state first so previous provider data is not shown.
      setCredentialSchema(null)
      setTempCredential({})
      setOauthPages([])

      const res = await fetchBuiltInToolCredentialSchema(collectionName)
      if (cancelled)
        return

      const toolCredentialSchemas = toolCredentialToFormSchemas(res)
      const credentialValue = await fetchBuiltInToolCredential(collectionName)
      if (cancelled)
        return

      const defaultCredentials = addDefaultValue(credentialValue, toolCredentialSchemas)
      setCredentialSchema(toolCredentialSchemas)
      setTempCredential(defaultCredentials)
    }

    loadCredential()

    return () => {
      cancelled = true
    }
  }, [collectionName])

  useEffect(() => {
    if (!isMessenger)
      return
    listMessengerChannels().then((res) => {
      const channels = res.data || []
      setExistingChannelIds(channels.map(channel => channel.channel_id))
      const selectedChannel = channels.find(channel => channel.channel_id === initialMessengerChannelId)
      const firstChannel = selectedChannel || channels[0]
      if (!firstChannel)
        return
      setChannelIdInput(firstChannel.channel_id)
      setChannelNameInput(firstChannel.name || 'Messenger Main Channel')
      setChannelAppIdInput(firstChannel.app_id || '')
      setChannelVerifyTokenInput('')
      setChannelEnabledInput(firstChannel.enabled !== false)
    }).catch(() => {
      // Ignore load error and allow manual setup.
      setExistingChannelIds([])
    })
  }, [initialMessengerChannelId, isMessenger])

  const handleSave = async () => {
    for (const field of credentialSchema) {
      if (field.required && !tempCredential[field.name]) {
        toast.error(t('errorMsg.fieldRequired', { ns: 'common', field: field.label[language] || field.label.en_US }))
        return
      }
    }
    setIsLoading(true)
    try {
      await onSaved(tempCredential)
      setIsLoading(false)
    }
    finally {
      setIsLoading(false)
    }
  }

  const handleConnectFacebook = async () => {
    const appId = String(tempCredential.app_id || '').trim()
    const appSecret = String(tempCredential.app_secret || '').trim()
    const graphApiVersion = String(tempCredential.graph_api_version || 'v23.0').trim() || 'v23.0'
    if (!appId || !appSecret) {
      toast.error('Please enter Facebook App ID and App Secret first.')
      return
    }

    setIsLoading(true)
    try {
      const res = await getMessengerOAuthAuthorizationUrl({
        app_id: appId,
        app_secret: appSecret,
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
        setTempCredential((prev: Record<string, any>) => ({
          ...prev,
          page_id: String(firstPage.id),
          page_access_token: String(firstPage.access_token),
          graph_api_version: data?.messenger_oauth?.graph_api_version || graphApiVersion,
        }))
        toast.success('Facebook connected. Please confirm selected page, then save.')
      })
    }
    finally {
      setIsLoading(false)
    }
  }

  const handleSelectPage = (pageId: string) => {
    const selected = oauthPages.find((page: MessengerOAuthPage) => page.id === pageId)
    if (!selected)
      return
    setTempCredential((prev: Record<string, any>) => ({
      ...prev,
      page_id: selected.id,
      page_access_token: selected.access_token,
    }))
  }

  const handleSaveMessengerChannel = async () => {
    if (!channelIdInput.trim()) {
      toast.error('channel_id is required.')
      return
    }
    if (!channelAppIdInput.trim()) {
      toast.error('app_id is required.')
      return
    }
    const channelId = channelIdInput.trim()
    const isExistingChannel = existingChannelIds.includes(channelId)
    if (!String(tempCredential.page_id || '').trim()) {
      toast.error('page_id is required in Messenger credentials.')
      return
    }
    if (!String(tempCredential.app_secret || '').trim()) {
      toast.error('app_secret is required in Messenger credentials.')
      return
    }
    if (!String(tempCredential.page_access_token || '').trim()) {
      toast.error('page_access_token is required in Messenger credentials.')
      return
    }

    const payload = {
      channel_id: channelId,
      app_id: channelAppIdInput.trim(),
      name: channelNameInput.trim() || channelIdInput.trim(),
      page_id: String(tempCredential.page_id).trim(),
      app_secret: String(tempCredential.app_secret).trim(),
      page_access_token: String(tempCredential.page_access_token).trim(),
      graph_api_version: String(tempCredential.graph_api_version || 'v23.0').trim() || 'v23.0',
      enabled: channelEnabledInput,
    }

    setIsSavingChannel(true)
    try {
      if (!isExistingChannel) {
        if (!channelVerifyTokenInput.trim()) {
          toast.error('verify_token is required for a new channel.')
          return
        }
        await createMessengerChannel({
          ...payload,
          verify_token: channelVerifyTokenInput.trim(),
        })
        toast.success('Messenger channel created.')
      }
      else {
        const updatePayload: Record<string, unknown> = {
          app_id: payload.app_id,
          name: payload.name,
          page_id: payload.page_id,
          graph_api_version: payload.graph_api_version,
          enabled: payload.enabled,
        }
        if (channelVerifyTokenInput.trim())
          updatePayload.verify_token = channelVerifyTokenInput.trim()
        if (payload.app_secret)
          updatePayload.app_secret = payload.app_secret
        if (payload.page_access_token)
          updatePayload.page_access_token = payload.page_access_token

        await updateMessengerChannel(payload.channel_id, updatePayload)
        toast.success('Messenger channel updated.')
      }
      await onMessengerChannelsUpdated?.()
      const refreshed = await listMessengerChannels()
      setExistingChannelIds((refreshed.data || []).map(channel => channel.channel_id))
    }
    finally {
      setIsSavingChannel(false)
    }
  }

  const handleLoadChannel = async (channelId: string) => {
    const channels = await listMessengerChannels()
    const selected = (channels.data || []).find(channel => channel.channel_id === channelId)
    if (!selected)
      return
    setChannelIdInput(selected.channel_id)
    setChannelNameInput(selected.name || 'Messenger Main Channel')
    setChannelAppIdInput(selected.app_id || '')
    setChannelVerifyTokenInput('')
    setChannelEnabledInput(selected.enabled !== false)
  }

  return (
    <Drawer
      isShow
      onHide={onCancel}
      dialogClassName="z-[1200]"
      title={t('auth.setupModalTitle', { ns: 'tools' }) as string}
      titleDescription={t('auth.setupModalTitleDescription', { ns: 'tools' }) as string}
      panelClassName="mt-[64px] mb-2 w-[420px]! border-components-panel-border"
      maxWidthClassName="max-w-[420px]!"
      height="calc(100vh - 64px)"
      contentClassName="bg-components-panel-bg!"
      headerClassName="border-b-divider-subtle!"
      body={(
        <div className="h-full px-6 py-3">
          {!credentialSchema
            ? <Loading type="app" />
            : (
                <>
                  <Form
                    value={tempCredential}
                    onChange={(v) => {
                      setTempCredential(v)
                    }}
                    formSchemas={credentialSchema}
                    isEditMode={true}
                    showOnVariableMap={{}}
                    validating={false}
                    inputClassName="bg-components-input-bg-normal!"
                    fieldMoreInfo={item => item.url
                      ? (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center text-xs text-text-accent"
                          >
                            {t('howToGet', { ns: 'tools' })}
                            <LinkExternal02 className="ml-1 h-3 w-3" />
                          </a>
                        )
                      : null}
                  />
                  {isMessenger && (
                    <div className="mb-3 rounded-xl border border-components-panel-border p-3">
                      <div className="mb-2 system-xs-medium-uppercase text-text-tertiary">Facebook Connection</div>
                      <Button
                        variant="secondary"
                        className="w-full"
                        onClick={handleConnectFacebook}
                        loading={isLoading}
                        disabled={isLoading}
                      >
                        Connect Facebook and Load Pages
                      </Button>
                      {!!oauthPages.length && (
                        <div className="mt-3">
                          <div className="mb-1 system-xs-regular text-text-tertiary">Select Facebook Page</div>
                          <select
                            className="w-full rounded-lg border border-components-input-border bg-components-input-bg-normal px-2 py-2 text-text-primary"
                            value={String(tempCredential.page_id || '')}
                            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => handleSelectPage(e.target.value)}
                          >
                            {oauthPages.map((page: MessengerOAuthPage) => (
                              <option key={page.id} value={page.id}>
                                {page.name} ({page.id})
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>
                  )}
                  {isMessenger && (
                    <div className="mb-3 rounded-xl border border-components-panel-border p-3">
                      <div className="mb-2 system-xs-medium-uppercase text-text-tertiary">{t('settings.channelsWebhookConnection', { ns: 'common' })}</div>
                      {!!existingChannelIds.length && (
                        <div className="mb-2">
                          <div className="mb-1 system-xs-regular text-text-tertiary">{t('settings.channelsExisting', { ns: 'common' })}</div>
                          <select
                            className="w-full rounded-lg border border-components-input-border bg-components-input-bg-normal px-2 py-2 text-text-primary"
                            value={channelIdInput}
                            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => handleLoadChannel(e.target.value)}
                          >
                            {existingChannelIds.map(channelId => (
                              <option key={channelId} value={channelId}>{channelId}</option>
                            ))}
                          </select>
                        </div>
                      )}
                      <div className="mb-2 system-xs-regular text-text-tertiary">
                        {t('settings.channelsWebhookDescription', { ns: 'common' })}
                      </div>
                      <div className="mb-2 grid grid-cols-1 gap-2">
                        <input
                          className="w-full rounded-lg border border-components-input-border bg-components-input-bg-normal px-2 py-2 text-text-primary"
                          placeholder="channel_id (e.g. fb-main)"
                          value={channelIdInput}
                          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setChannelIdInput(e.target.value)}
                        />
                        <input
                          className="w-full rounded-lg border border-components-input-border bg-components-input-bg-normal px-2 py-2 text-text-primary"
                          placeholder="channel name"
                          value={channelNameInput}
                          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setChannelNameInput(e.target.value)}
                        />
                        <input
                          className="w-full rounded-lg border border-components-input-border bg-components-input-bg-normal px-2 py-2 text-text-primary"
                          placeholder="app_id (Dify app UUID)"
                          value={channelAppIdInput}
                          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setChannelAppIdInput(e.target.value)}
                        />
                        <input
                          className="w-full rounded-lg border border-components-input-border bg-components-input-bg-normal px-2 py-2 text-text-primary"
                          placeholder={existingChannelIds.includes(channelIdInput.trim()) ? 'verify_token (optional to keep current)' : 'verify_token'}
                          value={channelVerifyTokenInput}
                          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setChannelVerifyTokenInput(e.target.value)}
                        />
                        <label className="flex items-center gap-2 text-sm text-text-secondary">
                          <input
                            type="checkbox"
                            checked={channelEnabledInput}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setChannelEnabledInput(e.target.checked)}
                          />
                          Channel enabled
                        </label>
                      </div>
                      {callbackUrl && (
                        <div className="mb-3 rounded-lg bg-background-default px-2 py-2 text-xs text-text-secondary">
                          Callback URL: {callbackUrl}
                        </div>
                      )}
                      <Button
                        variant="secondary"
                        className="w-full"
                        onClick={handleSaveMessengerChannel}
                        loading={isSavingChannel}
                        disabled={isSavingChannel}
                      >
                        Save Channel
                      </Button>
                    </div>
                  )}
                  <div className={cn((collection.is_team_authorization && !isHideRemoveBtn) ? 'justify-between' : 'justify-end', 'mt-2 flex ')}>
                    {
                      (collection.is_team_authorization && !isHideRemoveBtn) && (
                        <Button onClick={onRemove}>{t('operation.remove', { ns: 'common' })}</Button>
                      )
                    }
                    <div className="flex space-x-2">
                      <Button onClick={onCancel}>{t('operation.cancel', { ns: 'common' })}</Button>
                      <Button loading={isLoading || isSaving} disabled={isLoading || isSaving} variant="primary" onClick={handleSave}>{t('operation.save', { ns: 'common' })}</Button>
                    </div>
                  </div>
                </>
              )}

        </div>
      )}
      isShowMask={true}
      clickOutsideNotOpen={false}
    />
  )
}
export default React.memo(ConfigCredential)
