import { beforeEach, describe, expect, it, vi } from 'vitest'

const sdk = vi.hoisted(() => ({
  getTokenSilently: vi.fn().mockResolvedValue('gator-token'),
  handleRedirectCallback: vi.fn(), isAuthenticated: vi.fn().mockResolvedValue(true),
  loginWithRedirect: vi.fn(), logout: vi.fn(),
}))
vi.mock('@auth0/auth0-spa-js', () => ({ createAuth0Client: vi.fn().mockResolvedValue(sdk) }))
import { api, draftApi, draftToken, claimDraft, finishLogin } from './gator-api'

beforeEach(() => {
  const stored = new Map<string, string>()
  const storage = { getItem: (key: string) => stored.get(key) ?? null, setItem: (key: string, value: string) => stored.set(key, value) }
  vi.stubGlobal('window', { localStorage: storage, location: { origin: 'https://board.example', pathname: '/gatorize', search: '' }, history: { replaceState: vi.fn() } })
  vi.stubGlobal('fetch', vi.fn())
  vi.clearAllMocks()
})

describe('Gator Pass API boundary', () => {
  it('uploads multipart with the Auth0 bearer without overriding the browser boundary', async () => {
    const body = new FormData(); body.append('photos', new Blob(['photo'], { type: 'image/png' }), 'me.png')
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ job_id: 'job-1' })))
    expect(await api('/characters', { method: 'POST', body })).toEqual({ job_id: 'job-1' })
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(url).toBe('https://api.gatorcamp.us/characters')
    expect(init?.body).toBe(body)
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer gator-token')
    expect(new Headers(init?.headers).has('Content-Type')).toBe(false)
  })
  it('surfaces API capacity errors and handles non-JSON outages', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Capacity reached' }), { status: 429 }))
    await expect(api('/characters')).rejects.toThrow('Capacity reached')
    vi.mocked(fetch).mockResolvedValueOnce(new Response('Service unavailable', { status: 503 }))
    await expect(api('/me')).rejects.toThrow('503')
  })
  it('lets the SDK validate OAuth callback state before clearing query parameters', async () => {
    window.location.search = '?code=test-code&state=test-state'
    await finishLogin()
    expect(sdk.handleRedirectCallback).toHaveBeenCalledOnce()
    expect(window.history.replaceState).toHaveBeenCalledWith({}, '', '/gatorize')
  })
})

it('persists a random draft key before uploading without consulting Auth0', async () => {
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ job_id: 'draft' })))
  await draftApi('/characters', { method: 'POST', body: new FormData() })
  const key = draftToken()
  expect(key).toMatch(/^[0-9a-f]{64}$/)
  expect(window.localStorage.getItem('sgl-draft-key')).toBe(key)
  expect(sdk.getTokenSilently).not.toHaveBeenCalled()
  const [url, init] = vi.mocked(fetch).mock.calls[0]
  expect(url).not.toContain(key!)
  expect(new Headers(init?.headers).get('Authorization')).toBe(`Guest ${key}`)
  expect(draftToken(true)).toBe(key)
})

it('claims with both the verified user bearer and the private draft key', async () => {
  const key = draftToken(true)
  vi.mocked(fetch).mockResolvedValue(new Response('{}'))
  await claimDraft('my-draft')
  const [url, init] = vi.mocked(fetch).mock.calls[0]
  expect(url).toBe('https://api.gatorcamp.us/characters/my-draft/claim')
  expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer gator-token')
  expect(JSON.parse(init?.body as string)).toEqual({ draft_token: key })
})
