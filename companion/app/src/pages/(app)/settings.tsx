import { useState } from 'react'
import { logout } from '../../lib/gator-api'
import { refreshGatorSession, useGatorSession } from '../../lib/gator-session'
import GatorAccount from '../../components/GatorAccount'
import { GatorSignIn } from '../../components/GatorSignIn'

export default function SettingsPage() {
  const session = useGatorSession()
  const [error, setError] = useState('')
  return <div className="settings-page">
    <header className="settings-header"><p>SETTINGS · GATOR PASS</p><h1>Your account.</h1><p className="settings-sub">One account for your characters, campus records, and the game.</p></header>
    {!session.loaded ? <p role="status">Loading your account…</p> : !session.signedIn ? <section className="settings-card">
      <h2>Sign in with Gator Pass</h2><p>Use the same account here and in the game. New here? Create your Gator Pass to get started.</p>
      {session.error && <p role="alert">Sign-in is unavailable: {session.error} <button className="underline" onClick={() => void refreshGatorSession()}>Retry</button></p>}
      <GatorSignIn />
    </section> : <>
      <section className="settings-card"><h2>Identity</h2>
        <ul className="settings-rows"><li><span className="settings-label">Name</span><span className="settings-value" data-testid="nav-user-name">{session.name ?? 'Gator'}</span></li><li><span className="settings-label">Email</span><span className="settings-value" data-testid="nav-user-email">{session.email ?? 'Not provided'}</span></li></ul>
        <button className="app-nav-signin settings-signout" onClick={() => void logout().catch((e: Error) => setError(e.message))}>Sign out</button>
      </section>
      <GatorAccount onDeleted={() => { window.localStorage.removeItem('sgl-last-job'); window.localStorage.removeItem('sgl-pending-claim') }} />
    </>}
    {error && <p role="alert">{error}</p>}
  </div>
}
