/**
 * Optional sidecar for Zalo Personal (zca-js) — QR login, inbound listener, outbound send.
 */
import express from 'express'
import { Zalo, LoginQRCallbackEventType, ThreadType } from 'zca-js'

const PORT = Number(process.env.PORT || 3920)
const sessions = new Map()

const app = express()
app.use(express.json())

function sessionState(channelId) {
  return sessions.get(channelId)
}

function ensureWebhookConfigured(channelId, state) {
  if (!state?.webhookUrl || !state?.verifyToken || !state.api)
    return
  if (state.webhookConfigured)
    return
  state.webhookConfigured = true
  state.api.listener.on('message', async (message) => {
    if (message.isSelf)
      return
    const content = message.data?.content
    if (typeof content !== 'string' || !content.trim())
      return
    const payload = {
      event: 'message',
      thread_id: String(message.threadId || ''),
      thread_type: message.type === ThreadType.Group ? 'group' : 'user',
      is_self: Boolean(message.isSelf),
      message_id: String(message.data?.msgId || message.data?.realMsgId || ''),
      text: content.trim(),
      sender_name: String(message.data?.dName || ''),
      timestamp: message.data?.ts || Date.now(),
    }
    try {
      await fetch(state.webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Omnichannel-Verify-Token': state.verifyToken,
        },
        body: JSON.stringify(payload),
      })
    }
    catch (err) {
      console.error(`webhook forward failed channel=${channelId}`, err?.message || err)
    }
  })
  try {
    state.api.listener.start()
  }
  catch (err) {
    console.error(`listener start failed channel=${channelId}`, err?.message || err)
  }
}

app.get('/healthz', (_req, res) => {
  res.json({ ok: true })
})

app.get('/channels/:channelId/login/status', (req, res) => {
  const state = sessionState(req.params.channelId)
  if (!state)
    return res.status(404).json({ status: 'pending_qr' })
  res.json({ status: state.status })
})

app.post('/channels/:channelId/webhook/configure', (req, res) => {
  const channelId = req.params.channelId
  const webhookUrl = String(req.body?.webhook_url || '').trim()
  const verifyToken = String(req.body?.verify_token || '').trim()
  const state = sessionState(channelId) || { status: 'pending_qr' }
  state.webhookUrl = webhookUrl
  state.verifyToken = verifyToken
  sessions.set(channelId, state)
  if (state.status === 'connected' && state.api)
    ensureWebhookConfigured(channelId, state)
  res.json({ ok: true })
})

app.post('/channels/:channelId/messages/send', async (req, res) => {
  const channelId = req.params.channelId
  const state = sessionState(channelId)
  const api = state?.api || state?.zalo
  if (!state || state.status !== 'connected' || !api?.sendMessage)
    return res.status(409).json({ error: 'Zalo Personal session is not connected' })
  const threadId = String(req.body?.thread_id || '').trim()
  const text = String(req.body?.text || '').trim()
  if (!threadId || !text)
    return res.status(400).json({ error: 'thread_id and text are required' })
  try {
    const result = await api.sendMessage({ msg: text }, threadId, ThreadType.User)
    res.json({ ok: true, result })
  }
  catch (err) {
    res.status(500).json({ error: String(err?.message || err) })
  }
})

app.post('/channels/:channelId/login/start', async (req, res) => {
  const channelId = req.params.channelId
  const existing = sessionState(channelId)
  if (existing?.status === 'connected')
    return res.json({ status: 'connected', qr_data_uri: '' })

  try {
    const zalo = new Zalo({ selfListen: true })
    let settled = false
    const result = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        if (!settled) {
          settled = true
          reject(new Error('QR generation timeout'))
        }
      }, 120_000)

      zalo.loginQR({}, async (event) => {
        if (event.type === LoginQRCallbackEventType.QRCodeGenerated) {
          const img = event.data?.image || ''
          const dataUrl = img.startsWith('data:') ? img : `data:image/png;base64,${img}`
          if (!settled) {
            settled = true
            clearTimeout(timeout)
            const prev = sessionState(channelId) || {}
            sessions.set(channelId, { ...prev, status: 'pending_qr', zalo })
            resolve({ qr_data_uri: dataUrl, status: 'pending_qr' })
          }
        }
        if (event.type === LoginQRCallbackEventType.GotLoginInfo) {
          const prev = sessionState(channelId) || {}
          const next = {
            ...prev,
            status: 'connected',
            zalo,
            api: zalo,
            creds: event.data,
          }
          sessions.set(channelId, next)
          ensureWebhookConfigured(channelId, next)
        }
      }).catch((err) => {
        if (!settled) {
          settled = true
          clearTimeout(timeout)
          reject(err)
        }
      })
    })
    res.json(result)
  }
  catch (err) {
    sessions.set(channelId, { status: 'expired' })
    res.status(500).json({ error: String(err?.message || err) })
  }
})

app.listen(PORT, () => {
  console.log(`zalo-personal-worker listening on :${PORT}`)
})
