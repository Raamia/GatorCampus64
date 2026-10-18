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
  })
  return client
}

export async function finishLogin() {
  const c = await auth0()
  const query = new URLSearchParams(window.location.search)
  if (query.has('state') && (query.has('code') || query.has('error'))) {
    try { await c.handleRedirectCallback() }
    finally { window.history.replaceState({}, '', window.location.pathname) }
  }
  return c.isAuthenticated()
}

export async function login() { return (await auth0()).loginWithRedirect({ appState: { returnTo: window.location.pathname } }) }
export async function logout() { return (await auth0()).logout({ logoutParams: { returnTo: window.location.origin } }) }
export async function token() { return (await auth0()).getTokenSilently() }
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${await token()}`)
  const response = await fetch(`${publicConfig.apiBase}${path}`, { ...init, headers })
  if (!response.ok) {
    const detail = (await response.json().catch(() => null) as { detail?: unknown } | null)?.detail
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status}). Please try again.`)
  }
  return response.json() as Promise<T>
}
