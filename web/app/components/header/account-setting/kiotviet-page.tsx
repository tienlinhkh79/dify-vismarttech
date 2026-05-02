'use client'
import type { KiotVietConnection } from '@/service/tools'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import { toast } from '@/app/components/base/ui/toast'
import Drawer from '@/app/components/base/drawer-plus'
import {
  createKiotVietConnection,
  fetchBuiltInToolCredential,
  listKiotVietConnections,
  updateBuiltInToolCredential,
  updateKiotVietConnection,
} from '@/service/tools'

const KiotVietPage = () => {
  const { t } = useTranslation()
  const [connections, setConnections] = useState<KiotVietConnection[]>([])
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [editingConnection, setEditingConnection] = useState<KiotVietConnection | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [formValue, setFormValue] = useState<KiotVietConnection>({
    connection_id: '',
    name: '',
    client_id: '',
    client_secret: '',
    retailer_name: '',
    enabled: true,
  })

  const sanitizeConnectionId = (value: string) => {
    return value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
  }

  const syncLegacyCredential = async (payload: {
    client_id: string
    client_secret: string
    retailer_name: string
  }) => {
    await updateBuiltInToolCredential('kiotviet', {
      client_id: payload.client_id,
      client_secret: payload.client_secret,
      retailer_name: payload.retailer_name,
    })
  }

  const tryBackfillFromLegacyCredential = async () => {
    const legacy = await fetchBuiltInToolCredential('kiotviet')
    const clientId = String(legacy.client_id || '').trim()
    const clientSecret = String(legacy.client_secret || '').trim()
    const retailerName = String(legacy.retailer_name || '').trim()
    if (!clientId || !clientSecret || !retailerName)
      return

    const connectionId = sanitizeConnectionId(`kiotviet-${retailerName}`) || 'kiotviet-main'
    await createKiotVietConnection({
      connection_id: connectionId,
      name: retailerName,
      client_id: clientId,
      client_secret: clientSecret,
      retailer_name: retailerName,
      enabled: true,
    })
  }

  const loadConnections = async () => {
    const res = await listKiotVietConnections()
    const currentConnections = res.data || []
    if (currentConnections.length) {
      setConnections(currentConnections)
      return
    }

    try {
      await tryBackfillFromLegacyCredential()
      const refreshed = await listKiotVietConnections()
      setConnections(refreshed.data || [])
    }
    catch {
      setConnections([])
    }
  }

  useEffect(() => {
    loadConnections().catch(() => {
      setConnections([])
    })
  }, [])

  const openCreate = () => {
    setIsDrawerOpen(true)
    setEditingConnection(null)
    setFormValue({
      connection_id: '',
      name: '',
      client_id: '',
      client_secret: '',
      retailer_name: '',
      enabled: true,
    })
  }

  const openEdit = (connection: KiotVietConnection) => {
    setIsDrawerOpen(true)
    setEditingConnection(connection)
    setFormValue({
      connection_id: connection.connection_id,
      name: connection.name,
      client_id: connection.client_id,
      client_secret: '',
      retailer_name: connection.retailer_name,
      enabled: connection.enabled,
    })
  }

  const closeDrawer = () => {
    setIsDrawerOpen(false)
    setEditingConnection(null)
    setFormValue({
      connection_id: '',
      name: '',
      client_id: '',
      client_secret: '',
      retailer_name: '',
      enabled: true,
    })
  }

  const saveConnection = async () => {
    const nextConnectionId = sanitizeConnectionId(formValue.connection_id || formValue.name)
    if (!nextConnectionId || !formValue.name.trim() || !formValue.client_id.trim() || !formValue.retailer_name.trim()) {
      toast.error(t('settings.kiotvietErrorRequiredFields', { ns: 'common' }))
      return
    }
    if (!editingConnection && !String(formValue.client_secret || '').trim()) {
      toast.error(t('settings.kiotvietErrorClientSecretRequired', { ns: 'common' }))
      return
    }

    setIsSaving(true)
    try {
      if (!editingConnection) {
        await createKiotVietConnection({
          ...formValue,
          connection_id: nextConnectionId,
          name: formValue.name.trim(),
          client_id: formValue.client_id.trim(),
          client_secret: String(formValue.client_secret || '').trim(),
          retailer_name: formValue.retailer_name.trim(),
        })
        await syncLegacyCredential({
          client_id: formValue.client_id.trim(),
          client_secret: String(formValue.client_secret || '').trim(),
          retailer_name: formValue.retailer_name.trim(),
        })
      }
      else {
        const updatePayload: Partial<KiotVietConnection> = {
          name: formValue.name.trim(),
          client_id: formValue.client_id.trim(),
          retailer_name: formValue.retailer_name.trim(),
          enabled: formValue.enabled,
        }
        if (String(formValue.client_secret || '').trim())
          updatePayload.client_secret = String(formValue.client_secret || '').trim()
        await updateKiotVietConnection(editingConnection.connection_id, updatePayload)

        const legacy = await fetchBuiltInToolCredential('kiotviet')
        const secretForLegacy = String(formValue.client_secret || '').trim() || String(legacy.client_secret || '').trim()
        if (secretForLegacy) {
          await syncLegacyCredential({
            client_id: formValue.client_id.trim(),
            client_secret: secretForLegacy,
            retailer_name: formValue.retailer_name.trim(),
          })
        }
      }
      toast.success(t('api.actionSuccess', { ns: 'common' }))
      await loadConnections()
      closeDrawer()
    }
    finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="rounded-xl border border-components-panel-border bg-components-panel-bg px-4 py-3">
      <div className="mb-1 system-sm-semibold text-text-primary">{t('settings.kiotvietCredentials', { ns: 'common' })}</div>
      <div className="mb-3 system-xs-regular text-text-tertiary">{t('settings.kiotvietCredentialsDesc', { ns: 'common' })}</div>
      <div className="mb-3 flex justify-end">
        <Button
          size="small"
          onClick={openCreate}
        >
          {t('settings.kiotvietAdd', { ns: 'common' })}
        </Button>
      </div>
      {!connections.length && (
        <div className="system-xs-regular text-text-tertiary">{t('settings.kiotvietConnectionsEmpty', { ns: 'common' })}</div>
      )}
      {!!connections.length && (
        <div className="space-y-2">
          {connections.map(connection => (
            <div key={connection.connection_id} className="flex items-center justify-between rounded-lg border border-divider-subtle px-3 py-2">
              <div>
                <div className="system-sm-medium text-text-primary">{connection.name}</div>
                <div className="mt-0.5 system-xs-regular text-text-tertiary">
                  {connection.connection_id} · {connection.client_id} · {connection.enabled ? t('dataSource.website.active', { ns: 'common' }) : t('dataSource.website.inactive', { ns: 'common' })}
                </div>
              </div>
              <Button
                size="small"
                variant="secondary"
                onClick={() => openEdit(connection)}
              >
                {t('operation.edit', { ns: 'common' })}
              </Button>
            </div>
          ))}
        </div>
      )}
      {isDrawerOpen && (
        <Drawer
          isShow
          onHide={closeDrawer}
          dialogClassName="z-[1200]"
          title={t('settings.kiotvietConnectionModalTitle', { ns: 'common' })}
          panelClassName="mt-[64px] mb-2 w-[420px]! border-components-panel-border"
          maxWidthClassName="max-w-[420px]!"
          height="calc(100vh - 64px)"
          contentClassName="bg-components-panel-bg!"
          body={(
            <div className="space-y-3 px-6 py-4">
              <Input
                disabled={!!editingConnection}
                value={formValue.connection_id}
                onChange={e => setFormValue(prev => ({ ...prev, connection_id: e.target.value }))}
                placeholder={t('settings.kiotvietPlaceholderConnectionId', { ns: 'common' })}
              />
              <Input
                value={formValue.name}
                onChange={e => setFormValue(prev => ({ ...prev, name: e.target.value }))}
                placeholder={t('settings.kiotvietPlaceholderConnectionName', { ns: 'common' })}
              />
              <Input
                value={formValue.client_id}
                onChange={e => setFormValue(prev => ({ ...prev, client_id: e.target.value }))}
                placeholder={t('settings.kiotvietPlaceholderClientId', { ns: 'common' })}
              />
              <Input
                type="password"
                value={formValue.client_secret}
                onChange={e => setFormValue(prev => ({ ...prev, client_secret: e.target.value }))}
                placeholder={editingConnection
                  ? t('settings.kiotvietPlaceholderClientSecretOptional', { ns: 'common' })
                  : t('settings.kiotvietPlaceholderClientSecret', { ns: 'common' })}
              />
              <Input
                value={formValue.retailer_name}
                onChange={e => setFormValue(prev => ({ ...prev, retailer_name: e.target.value }))}
                placeholder={t('settings.kiotvietPlaceholderRetailerName', { ns: 'common' })}
              />
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={formValue.enabled}
                  onChange={e => setFormValue(prev => ({ ...prev, enabled: e.target.checked }))}
                />
                {t('settings.channelsEnabledLabel', { ns: 'common' })}
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <Button onClick={closeDrawer}>{t('operation.cancel', { ns: 'common' })}</Button>
                <Button loading={isSaving} disabled={isSaving} variant="primary" onClick={saveConnection}>
                  {t('operation.save', { ns: 'common' })}
                </Button>
              </div>
            </div>
          )}
        />
      )}
    </div>
  )
}

export default KiotVietPage
