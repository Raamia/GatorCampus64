import type { Hono } from 'hono'
import type { AppContext } from '../../worker.js'
import { resolveAuth } from './http-routes.js'
import { signIngest } from '../actions/verified-runs.js'
import config from '../lib/gator-config.json'

const hex = (bytes: ArrayBuffer) => Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join('')

export function registerIdentityRoutes(app: Hono<AppContext>): void {
  app.post('/api/account/identity', async c => {
    const auth = await resolveAuth(c.req.raw, c.env)
    if (!auth || auth.userId.startsWith('anon-')) return c.json({ detail: 'Sign in to Field Board first.' }, 401)
    if (!c.env.DEEPSPACE_INGEST_SECRET) return c.json({ detail: 'Account linking is unavailable.' }, 503)
    if (Number(c.req.header('content-length') ?? 0) > 20000) return c.json({ detail: 'Request too large.' }, 413)
    const raw = await c.req.text()
    if (raw.length > 20000) return c.json({ detail: 'Request too large.' }, 413)
    let input: { action?: unknown; gatorToken?: unknown }
    try { input = JSON.parse(raw) } catch { return c.json({ detail: 'Invalid request.' }, 400) }
    if (!input || !['link', 'unlink', 'status'].includes(String(input.action)) ||
        typeof input.gatorToken !== 'string' || !input.gatorToken || input.gatorToken.length > 16000) {
      return c.json({ detail: 'Choose a linking action and sign in to Gator Pass.' }, 400)
    }
    const enc = new TextEncoder()
    const body = JSON.stringify({ action: input.action, user_id: auth.userId,
      token_hash: hex(await crypto.subtle.digest('SHA-256', enc.encode(input.gatorToken))) })
    const key = await crypto.subtle.importKey('raw', enc.encode(c.env.DEEPSPACE_INGEST_SECRET),
      { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
    const secret = hex(await crypto.subtle.sign('HMAC', key, enc.encode('sgl-identity-v1')))
    const timestamp = String(Math.floor(Date.now() / 1000))
    const nonce = crypto.randomUUID().replaceAll('-', '')
    try {
      const response = await fetch(`${config.apiBase}/account/identity`, {
        method: 'POST', redirect: 'error', signal: AbortSignal.timeout(8000),
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${input.gatorToken}`,
          'X-SGL-Timestamp': timestamp, 'X-SGL-Nonce': nonce,
          'X-SGL-Signature': await signIngest(secret, body, timestamp, nonce) }, body,
      })
      return new Response(response.body, { status: response.status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } })
    } catch { return c.json({ detail: 'Gator Pass is unavailable. Please try again.' }, 503) }
  })
}
