import config from '../lib/gator-config.json'

/** Resolve identity through the game API's Auth0 verifier, never email or client claims. */
export async function resolveGatorAuth(request: Request): Promise<{ userId: string } | null> {
  const authorization = request.headers.get('Authorization')
  if (!authorization || !/^Bearer\s+\S+$/i.test(authorization)) return null
  try {
    const response = await fetch(`${config.apiBase}/me`, {
      headers: { Authorization: authorization }, signal: AbortSignal.timeout(5000), redirect: 'error',
    })
    if (!response.ok) return null
    const body = await response.json() as { user?: { sub?: unknown } }
    return typeof body.user?.sub === 'string' && body.user.sub.length > 0 ? { userId: body.user.sub } : null
  } catch { return null }
}
