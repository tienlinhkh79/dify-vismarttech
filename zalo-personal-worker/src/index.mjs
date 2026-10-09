/**
 * Optional sidecar for Zalo Personal (zca-js) — QR login, inbound listener, outbound send.
 * Persists cookie sessions to disk and runs keepAlive so QR re-scan is needed less often.
 */
import express from 'express'
import fs from 'fs'
import os from 'os'
import path from 'path'
import sharp from 'sharp'
import { Zalo, LoginQRCallbackEventType, ThreadType, DestType } from 'zca-js'

async function imageMetadataGetter(filePath) {
  const data = await fs.promises.readFile(filePath)
  const metadata = await sharp(data).metadata()
  return {
    height: metadata.height,
    width: metadata.width,
    size: metadata.size || data.length,
  }
}

const ZALO_OPTIONS = {
  selfListen: true,
  logging: true,
  imageMetadataGetter,
}

const PORT = Number(process.env.PORT || 3920)
const SESSION_DIR = process.env.SESSION_DIR || '/data/sessions'
// Cookie Zalo ~1h; refresh every 5 phút để giữ phiên ~30 ngày khi worker chạy liên tục.
const KEEPALIVE_INTERVAL_MS = Number(process.env.KEEPALIVE_INTERVAL_MS || 5 * 60 * 1000)
const SESSION_TARGET_DAYS = Number(process.env.SESSION_TARGET_DAYS || 30)
const SESSION_TARGET_MS = SESSION_TARGET_DAYS * 24 * 60 * 60 * 1000
const sessions = new Map()

const app = express()
app.use(express.json())

function sessionState(channelId) {
  return sessions.get(channelId)
}

function sessionFile(channelId) {
  return path.join(SESSION_DIR, `${channelId}.json`)
}

function webhookFile(channelId) {
  return path.join(SESSION_DIR, `${channelId}.webhook.json`)
}

function loadWebhookConfig(channelId) {
  const file = webhookFile(channelId)
  if (!fs.existsSync(file))
    return null
  try {
    const saved = JSON.parse(fs.readFileSync(file, 'utf-8'))
    const webhookUrl = String(saved.webhook_url || '').trim()
    const verifyToken = String(saved.verify_token || '').trim()
    if (!webhookUrl || !verifyToken)
      return null
    return { webhookUrl, verifyToken }
  }
  catch {
    return null
  }
}

function saveWebhookConfig(channelId, webhookUrl, verifyToken) {
  fs.mkdirSync(SESSION_DIR, { recursive: true })
  fs.writeFileSync(
    webhookFile(channelId),
    JSON.stringify({ webhook_url: webhookUrl, verify_token: verifyToken }),
  )
}

function toQrDataUri(image) {
  const img = String(image || '').trim()
  if (!img)
    return ''
  return img.startsWith('data:') ? img : `data:image/png;base64,${img}`
}

function toSeenMessageParam(data) {
  const raw = data || {}
  return {
    msgId: String(raw.msgId || ''),
    cliMsgId: String(raw.cliMsgId || ''),
    uidFrom: String(raw.uidFrom || ''),
    idTo: String(raw.idTo || ''),
    msgType: String(raw.msgType || ''),
    st: Number(raw.st ?? 1),
    at: Number(raw.at ?? 1),
    cmd: Number(raw.cmd ?? 1),
    ts: raw.ts ?? '',
  }
}

function toMessageMeta(data) {
  const raw = data || {}
  return {
    msgId: String(raw.msgId || ''),
    cliMsgId: String(raw.cliMsgId || ''),
    uidFrom: String(raw.uidFrom || ''),
    idTo: String(raw.idTo || ''),
    msgType: String(raw.msgType || ''),
    st: Number(raw.st ?? 1),
    at: Number(raw.at ?? 1),
    cmd: Number(raw.cmd ?? 1),
    ts: raw.ts ?? '',
  }
}

async function saveSessionCredentials(channelId, api) {
  const ctx = api.getContext()
  const jar = api.getCookie()
  const serialized = await jar.serialize()
  const data = {
    imei: ctx.imei,
    userAgent: ctx.userAgent,
    language: ctx.language,
    cookies: serialized,
    saved_at: Date.now(),
    session_target_days: SESSION_TARGET_DAYS,
  }
  fs.mkdirSync(SESSION_DIR, { recursive: true })
  fs.writeFileSync(sessionFile(channelId), JSON.stringify(data))
}

function startKeepAlive(channelId, state) {
  if (state.keepAliveTimer)
    clearInterval(state.keepAliveTimer)
  state.keepAliveTimer = setInterval(async () => {
    try {
      await runKeepAlivePulse(channelId, state)
    }
    catch (err) {
      console.error(`keepAlive failed channel=${channelId}`, err?.message || err)
    }
  }, KEEPALIVE_INTERVAL_MS)
}

async function runKeepAlivePulse(channelId, state) {
  if (!state.api?.keepAlive)
    return
  await state.api.keepAlive()
  await saveSessionCredentials(channelId, state.api)
}

async function connectSession(channelId, api, zalo, prev = {}) {
  const savedWebhook = loadWebhookConfig(channelId)
  const next = {
    ...prev,
    status: 'connected',
    api,
    zalo,
    loginInProgress: false,
    error: '',
    loginTask: null,
    webhookUrl: String(prev.webhookUrl || savedWebhook?.webhookUrl || '').trim(),
    verifyToken: String(prev.verifyToken || savedWebhook?.verifyToken || '').trim(),
    webhookConfigured: false,
  }
  sessions.set(channelId, next)
  try {
    await runKeepAlivePulse(channelId, next)
  }
  catch (err) {
    console.error(`initial keepAlive failed channel=${channelId}`, err?.message || err)
    try {
      await saveSessionCredentials(channelId, api)
    }
    catch (saveErr) {
      console.error(`save session failed channel=${channelId}`, saveErr?.message || saveErr)
    }
  }
  startKeepAlive(channelId, next)
  ensureWebhookConfigured(channelId, next)
}

async function restoreSessionFromDisk(channelId) {
  const file = sessionFile(channelId)
  if (!fs.existsSync(file))
    return false
  try {
    const saved = JSON.parse(fs.readFileSync(file, 'utf-8'))
    const savedAt = Number(saved.saved_at || 0)
    if (savedAt > 0 && Date.now() - savedAt > SESSION_TARGET_MS) {
      console.warn(
        `Zalo Personal session file older than ${SESSION_TARGET_DAYS}d channel=${channelId}; trying restore anyway`,
      )
    }
    const zalo = new Zalo(ZALO_OPTIONS)
    const api = await zalo.login({
      cookie: saved.cookies,
      imei: saved.imei,
      userAgent: saved.userAgent,
      language: saved.language,
    })
    const prev = sessionState(channelId) || {}
    await connectSession(channelId, api, zalo, prev)
    console.log(`Zalo Personal restored from disk channel=${channelId}`)
    return true
  }
  catch (err) {
    console.error(`Zalo Personal restore failed channel=${channelId}`, err?.message || err)
    return false
  }
}

function restoreAllSessions() {
  if (!fs.existsSync(SESSION_DIR))
    return
  for (const name of fs.readdirSync(SESSION_DIR)) {
    if (!name.endsWith('.json') || name.endsWith('.webhook.json'))
      continue
    const channelId = name.replace(/\.json$/, '')
    void restoreSessionFromDisk(channelId)
  }
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
      message_meta: toMessageMeta(message.data),
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

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function guessExtension(url, contentType) {
  const fromUrl = String(url || '').split('?')[0].split('.').pop()?.toLowerCase() || ''
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(fromUrl))
    return fromUrl === 'jpeg' ? 'jpg' : fromUrl
  const type = String(contentType || '').toLowerCase()
  if (type.includes('png'))
    return 'png'
  if (type.includes('gif'))
    return 'gif'
  if (type.includes('webp'))
    return 'webp'
  return 'jpg'
}

async function downloadImageToTemp(url) {
  const response = await fetch(url)
  if (!response.ok)
    throw new Error(`Failed to download image: ${url}`)
  const contentType = response.headers.get('content-type') || ''
  const ext = guessExtension(url, contentType)
  const filePath = path.join(
    os.tmpdir(),
    `zp-${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`,
  )
  const buffer = Buffer.from(await response.arrayBuffer())
  if (!buffer.length)
    throw new Error(`Empty image body: ${url}`)
  fs.writeFileSync(filePath, buffer)
  return filePath
}

async function cleanupTempFiles(files) {
  for (const file of files) {
    try {
      fs.unlinkSync(file)
    }
    catch {
      // ignore cleanup errors
    }
  }
}

async function runQrLogin(channelId) {
  const existing = sessionState(channelId)
  if (existing?.loginTask)
    return existing.loginTask

  const zalo = new Zalo(ZALO_OPTIONS)
  const task = (async () => {
    try {
      const api = await zalo.loginQR({}, (event) => {
        const prev = sessionState(channelId) || {}
        if (event.type === LoginQRCallbackEventType.QRCodeGenerated) {
          sessions.set(channelId, {
            ...prev,
            status: 'pending_qr',
            qr_data_uri: toQrDataUri(event.data?.image),
            loginInProgress: true,
            error: '',
            zalo,
          })
          return
        }
        if (event.type === LoginQRCallbackEventType.QRCodeScanned) {
          sessions.set(channelId, {
            ...sessionState(channelId),
            status: 'scanned',
            scanned_display_name: String(event.data?.display_name || '').trim(),
            error: '',
          })
          return
        }
        if (event.type === LoginQRCallbackEventType.QRCodeExpired) {
          sessions.set(channelId, {
            ...sessionState(channelId),
            status: 'expired',
            loginInProgress: false,
            error: 'QR code expired',
          })
          return
        }
        if (event.type === LoginQRCallbackEventType.QRCodeDeclined) {
          sessions.set(channelId, {
            ...sessionState(channelId),
            status: 'declined',
            loginInProgress: false,
            error: 'Login declined on phone',
          })
        }
      })

      const prev = sessionState(channelId) || {}
      await connectSession(channelId, api, zalo, prev)
      console.log(`Zalo Personal connected channel=${channelId}`)
    }
    catch (err) {
      console.error(`Zalo Personal login failed channel=${channelId}`, err?.message || err)
      const prev = sessionState(channelId) || {}
      sessions.set(channelId, {
        ...prev,
        status: 'expired',
        loginInProgress: false,
        loginTask: null,
        error: String(err?.message || err),
      })
    }
  })()

  sessions.set(channelId, {
    ...(existing || {}),
    status: 'starting',
    loginInProgress: true,
    loginTask: task,
    qr_data_uri: existing?.qr_data_uri || '',
    error: '',
    zalo,
  })
  return task
}

app.get('/healthz', (_req, res) => {
  res.json({ ok: true })
})

app.get('/channels/:channelId/login/status', (req, res) => {
  const state = sessionState(req.params.channelId)
  if (!state)
    return res.status(404).json({ status: 'pending_qr', connected: false })
  res.json({
    status: state.status || 'pending_qr',
    connected: state.status === 'connected',
    scanned_display_name: state.scanned_display_name || '',
    error: state.error || '',
  })
})

app.post('/channels/:channelId/webhook/configure', (req, res) => {
  const channelId = req.params.channelId
  const webhookUrl = String(req.body?.webhook_url || '').trim()
  const verifyToken = String(req.body?.verify_token || '').trim()
  const state = sessionState(channelId) || { status: 'pending_qr' }
  state.webhookUrl = webhookUrl
  state.verifyToken = verifyToken
  state.webhookConfigured = false
  sessions.set(channelId, state)
  if (webhookUrl && verifyToken)
    saveWebhookConfig(channelId, webhookUrl, verifyToken)
  if (state.status === 'connected' && state.api)
    ensureWebhookConfigured(channelId, state)
  else
    void restoreSessionFromDisk(channelId)
  res.json({ ok: true })
})

app.post('/channels/:channelId/presence/seen', async (req, res) => {
  const channelId = req.params.channelId
  const state = sessionState(channelId)
  const api = state?.api
  if (!state || state.status !== 'connected' || !api?.sendSeenEvent)
    return res.status(409).json({ error: 'Zalo Personal session is not connected' })
  const message = req.body?.message
  if (!message || typeof message !== 'object')
    return res.status(400).json({ error: 'message metadata is required' })
  try {
    const result = await api.sendSeenEvent(
      toSeenMessageParam(message),
      ThreadType.User,
    )
    res.json({ ok: true, result })
  }
  catch (err) {
    res.status(500).json({ error: String(err?.message || err) })
  }
})

app.post('/channels/:channelId/presence/typing', async (req, res) => {
  const channelId = req.params.channelId
  const state = sessionState(channelId)
  const api = state?.api
  if (!state || state.status !== 'connected' || !api?.sendTypingEvent)
    return res.status(409).json({ error: 'Zalo Personal session is not connected' })
  const threadId = String(req.body?.thread_id || '').trim()
  if (!threadId)
    return res.status(400).json({ error: 'thread_id is required' })
  try {
    const result = await api.sendTypingEvent(threadId, ThreadType.User, DestType.User)
    res.json({ ok: true, result })
  }
  catch (err) {
    res.status(500).json({ error: String(err?.message || err) })
  }
})

app.post('/channels/:channelId/messages/send', async (req, res) => {
  const channelId = req.params.channelId
  const state = sessionState(channelId)
  const api = state?.api
  if (!state || state.status !== 'connected' || !api?.sendMessage)
    return res.status(409).json({ error: 'Zalo Personal session is not connected' })
  const threadId = String(req.body?.thread_id || '').trim()
  const text = String(req.body?.text || '').trim()
  const rawImageUrls = Array.isArray(req.body?.image_urls) ? req.body.image_urls : []
  const imageUrls = rawImageUrls
    .map(item => String(item || '').trim())
    .filter(url => url.toLowerCase().startsWith('https://'))
    .slice(0, 3)
  if (!threadId || (!text && !imageUrls.length))
    return res.status(400).json({ error: 'thread_id and text or image_urls are required' })

  const tempFiles = []
  try {
    for (const imageUrl of imageUrls)
      tempFiles.push(await downloadImageToTemp(imageUrl))

    const message = tempFiles.length
      ? { msg: text, attachments: tempFiles }
      : { msg: text }
    const result = await api.sendMessage(message, threadId, ThreadType.User)
    res.json({ ok: true, result })
  }
  catch (err) {
    res.status(500).json({ error: String(err?.message || err) })
  }
  finally {
    await cleanupTempFiles(tempFiles)
  }
})

app.post('/channels/:channelId/login/start', async (req, res) => {
  const channelId = req.params.channelId
  const existing = sessionState(channelId)
  if (existing?.status === 'connected')
    return res.json({ status: 'connected', qr_data_uri: '', connected: true })

  if (!existing?.loginInProgress && await restoreSessionFromDisk(channelId)) {
    return res.json({ status: 'connected', qr_data_uri: '', connected: true })
  }

  if (existing?.qr_data_uri && existing.loginInProgress) {
    return res.json({
      qr_data_uri: existing.qr_data_uri,
      status: existing.status || 'pending_qr',
      connected: false,
    })
  }

  try {
    void runQrLogin(channelId)
    const deadline = Date.now() + 45_000
    while (Date.now() < deadline) {
      const state = sessionState(channelId)
      if (state?.error && !state?.qr_data_uri)
        return res.status(500).json({ error: state.error })
      if (state?.qr_data_uri) {
        return res.json({
          qr_data_uri: state.qr_data_uri,
          status: state.status || 'pending_qr',
          connected: state.status === 'connected',
        })
      }
      if (state?.status === 'connected') {
        return res.json({ status: 'connected', qr_data_uri: '', connected: true })
      }
      await sleep(250)
    }
    return res.status(504).json({ error: 'QR generation timeout' })
  }
  catch (err) {
    sessions.set(channelId, { status: 'expired', error: String(err?.message || err) })
    return res.status(500).json({ error: String(err?.message || err) })
  }
})

restoreAllSessions()

app.listen(PORT, () => {
  console.log(`zalo-personal-worker listening on :${PORT}`)
})
