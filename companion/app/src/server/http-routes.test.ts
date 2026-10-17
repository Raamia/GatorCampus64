import { describe, expect, it } from 'vitest'
import { socialLoginUrl } from './http-routes.js'

describe('socialLoginUrl', () => {
  it('returns browser OAuth to the app callback that exchanges the code and sets the session cookie', () => {
    const redirect = new URL(socialLoginUrl(
      'https://gator-field-board.app.space/api/auth/social-redirect?provider=google',
      'https://auth.deep.space/',
      'google',
    ))

    expect(redirect.origin).toBe('https://auth.deep.space')
    expect(redirect.pathname).toBe('/login/social')
    expect(redirect.searchParams.get('provider')).toBe('google')
    expect(redirect.searchParams.get('returnTo')).toBe(
      'https://gator-field-board.app.space/api/auth/oauth-complete',
    )
  })
})
