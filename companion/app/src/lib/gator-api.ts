import { createAuth0Client, type Auth0Client } from '@auth0/auth0-spa-js'

import publicConfig from './gator-config.json'

let client: Promise<Auth0Client> | undefined
function auth0() {
  client ??= createAuth0Client({
    domain: publicConfig.domain,
    clientId: publicConfig.clientId,
    cacheLocation: 'localstorage',
    useRefreshTokens: false,
    authorizationParams: { audience: publicConfig.audience, scope: 'openid profile email create:character read:own', redirect_uri: window.location.origin + '/gatorize' },
  }).catch(error => { client = undefined; throw error })
  return client
}

let finishing: Promise<boolean> | undefined
export function finishLogin(): Promise<boolean> {
  // The header and page share the callback; OAuth codes can only be consumed once.
  finishing ??= completeLogin().finally(() => { finishing = undefined })
  return finishing
}
async function completeLogin() {
  const c = await auth0()
  const query = new URLSearchParams(window.location.search)
  if (query.has('state') && (query.has('code') || query.has('error'))) {
    let returnTo: unknown
    try { returnTo = (await c.handleRedirectCallback())?.appState?.returnTo }
    finally { window.history.replaceState({}, '', window.location.pathname) }
    // Keep the existing allowed Auth0 callback URI; only navigate locally afterward.
    if (typeof returnTo === 'string' && returnTo.startsWith('/') && !returnTo.startsWith('//') && !returnTo.includes('\\')) {
      const target = new URL(returnTo, window.location.origin)
      if (target.origin === window.location.origin && target.pathname !== window.location.pathname) window.location.replace(target.pathname + target.search + target.hash)
    }
  }
  return c.isAuthenticated()
}

export async function login(fresh = false) {
  return (await auth0()).loginWithRedirect({ ...(fresh ? { authorizationParams: { prompt: 'login' } } : {}), appState: { returnTo: window.location.pathname } })
}
export async function signup() {
  return (await auth0()).loginWithRedirect({ authorizationParams: { screen_hint: 'signup' }, appState: { returnTo: window.location.pathname } })
}
export async function profile() { return (await auth0()).getUser() }
export async function logout() { return (await auth0()).logout({ logoutParams: { returnTo: window.location.origin } }) }
export async function token() { return (await auth0()).getTokenSilently() }
const draftKey = 'sgl-draft-key'
export function draftToken(create = false): string | null {
  const saved = window.localStorage.getItem(draftKey)
  if (saved && /^[0-9a-f]{64}$/.test(saved)) return saved
  if (!create) return null
  const value = Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2, '0')).join('')
  // Persist before uploading: losing this key would make the draft inaccessible.
  window.localStorage.setItem(draftKey, value)
  return value
}

async function request<T>(path: string, init: RequestInit, authorization: string): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Authorization', authorization)
  const response = await fetch(`${publicConfig.apiBase}${path}`, { ...init, headers })
  if (!response.ok) {
    const detail = (await response.json().catch(() => null) as { detail?: unknown } | null)?.detail
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status}). Please try again.`)
  }
  return response.json() as Promise<T>
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  return request<T>(path, init, `Bearer ${await token()}`)
}
export async function draftApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  return request<T>(path, init, `Guest ${draftToken(true)}`)
}
export async function claimDraft(characterId: string) {
  const key = draftToken()
  if (!key) throw new Error('This browser no longer has the key for your draft. Please build a new gator.')
  return api(`/characters/${encodeURIComponent(characterId)}/claim`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ draft_token: key }),
  })
}
