import { beforeEach, describe, expect, it, vi } from 'vitest'

const sdk = vi.hoisted(() => ({
  getTokenSilently: vi.fn().mockResolvedValue('gator-token'),
  handleRedirectCallback: vi.fn(), isAuthenticated: vi.fn().mockResolvedValue(true),
  loginWithRedirect: vi.fn(), logout: vi.fn(),
}))
vi.mock('@auth0/auth0-spa-js', () => ({ createAuth0Client: vi.fn().mockResolvedValue(sdk) }))
import { api, finishLogin } from './gator-api'

beforeEach(() => {
  vi.stubGlobal('window', { location: { origin: 'https://board.example', pathname: '/gatorize', search: '' }, history: { replaceState: vi.fn() } })
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
