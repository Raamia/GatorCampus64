import { Hono } from 'hono'
import { beforeEach, expect, it, vi } from 'vitest'
import type { AppContext, Env } from '../../worker.js'
import { registerIdentityRoutes } from './identity-routes.js'
import { verifyIngestSignature } from '../actions/verified-runs.js'
vi.mock('./http-routes.js', () => ({ resolveAuth: async (req: Request) =>
  req.headers.get('Authorization') === 'Bearer valid-board-token' ? { userId: 'verified-board-user' } : null }))
const app = new Hono<AppContext>()
registerIdentityRoutes(app)
const env = { DEEPSPACE_INGEST_SECRET: 'test-identity-secret' } as Env
const request = (auth = true, body: unknown = { action: 'link', gatorToken: 'gator-token', user_id: 'forged-user' }) =>
  app.request('/api/account/identity', { method: 'POST', headers: { 'Content-Type': 'application/json',
    ...(auth ? { Authorization: 'Bearer valid-board-token' } : {}) }, body: JSON.stringify(body) }, env)
beforeEach(() => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ linked: true }))) })
it('requires Field Board auth before using either token', async () => {
  expect((await request(false)).status).toBe(401)
  expect(fetch).not.toHaveBeenCalled()
})
it('binds verified identity and action to the exact Gator token with a distinct signing key', async () => {
  expect((await request()).status).toBe(200)
  const [url, init] = vi.mocked(fetch).mock.calls[0]
  expect(url).toBe('https://api.gatorcamp.us/account/identity')
  const data = JSON.parse(String(init?.body))
  expect(data.user_id).toBe('verified-board-user')
  expect(data.action).toBe('link')
  const enc = new TextEncoder()
  const hex = (a: ArrayBuffer) => Array.from(new Uint8Array(a), b => b.toString(16).padStart(2, '0')).join('')
  expect(data.token_hash).toBe(hex(await crypto.subtle.digest('SHA-256', enc.encode('gator-token'))))
  const key = await crypto.subtle.importKey('raw', enc.encode(env.DEEPSPACE_INGEST_SECRET!), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
  const secret = hex(await crypto.subtle.sign('HMAC', key, enc.encode('sgl-identity-v1')))
  const headers = new Headers(init?.headers)
  const proof = { secret, body: String(init?.body), timestamp: headers.get('x-sgl-timestamp'), nonce: headers.get('x-sgl-nonce'), signature: headers.get('x-sgl-signature') }
  expect(await verifyIngestSignature(proof)).toBe('ok')
  expect(await verifyIngestSignature({ ...proof, secret: env.DEEPSPACE_INGEST_SECRET! })).toBe('bad_signature')
  expect(headers.get('Authorization')).toBe('Bearer gator-token')
  expect(init?.redirect).toBe('error')
})
it('rejects malformed requests and fails closed on upstream outage', async () => {
  expect((await request(true, { action: 'delete', gatorToken: 'x' })).status).toBe(400)
  vi.mocked(fetch).mockRejectedValue(new Error('offline'))
  expect((await request()).status).toBe(503)
})
