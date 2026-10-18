import { afterEach, expect, it, vi } from 'vitest'
import { resolveGatorAuth } from './gator-auth'
afterEach(() => vi.unstubAllGlobals())
const request = (auth?: string) => new Request('https://board.example/api/study/events', { headers: auth ? { Authorization: auth, 'x-user-id': 'forged-user' } : {} })
it('uses only the verified game API subject and forwards no caller identity headers', async () => {
  const fetcher = vi.fn().mockResolvedValue(Response.json({ user: { sub: 'auth0|alice' } }))
  vi.stubGlobal('fetch', fetcher)
  expect(await resolveGatorAuth(request('Bearer opaque-token'))).toEqual({ userId: 'auth0|alice' })
  expect(fetcher).toHaveBeenCalledWith('https://api.gatorcamp.us/me', expect.objectContaining({ headers: { Authorization: 'Bearer opaque-token' }, redirect: 'error' }))
})
it.each([401, 403, 503])('fails closed when the API returns %s', async status => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status })))
  expect(await resolveGatorAuth(request('Bearer invalid'))).toBeNull()
})
it('rejects absent and non-user credentials without contacting the API', async () => {
  const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher)
  for (const header of [undefined, 'Guest private-key', 'Basic value']) expect(await resolveGatorAuth(request(header))).toBeNull()
  expect(fetcher).not.toHaveBeenCalled()
})
it('fails closed on timeouts and malformed upstream identities', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error('timeout')).mockResolvedValueOnce(Response.json({ user: { sub: 42 } })))
  expect(await resolveGatorAuth(request('Bearer token'))).toBeNull()
  expect(await resolveGatorAuth(request('Bearer token'))).toBeNull()
})
