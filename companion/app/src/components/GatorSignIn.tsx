import { useState } from 'react'
import { login, signup } from '../lib/gator-api'

export function GatorSignIn({ compact = false }: { compact?: boolean }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function start(create: boolean) {
    setError(''); setBusy(true)
    try { await (create ? signup() : login()) }
    catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }
  return <div className={compact ? 'gator-auth-actions' : 'gator-auth-panel'}>
    <div className="gator-auth-buttons">
      <button data-testid={compact ? 'nav-sign-in-button' : undefined} className="app-nav-signin" disabled={busy} onClick={() => void start(false)}>Sign in</button>
      <button data-testid={compact ? 'nav-sign-up-button' : undefined} className="app-nav-signin gator-signup" disabled={busy} onClick={() => void start(true)}>Sign up</button>
    </div>
    {error && <p role="alert" className="gator-auth-error">{error}</p>}
  </div>
}
