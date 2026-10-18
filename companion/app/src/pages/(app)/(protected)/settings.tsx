/**
 * Reached at /settings — no auth logic lives here because
 * (protected)/_layout.tsx already wraps the subtree in <AuthGate>.
 */

import { signOut, useUser } from 'deepspace'
import { Avatar, AvatarFallback, AvatarImage, Button } from '@/components/ui'

export default function SettingsPage() {
  const { user } = useUser()
  return (
    // No background on page wrappers — pages render into whatever the app's
    // (app)/_layout provides (a plain background, or a raised panel), so they
    // stay transparent and inherit it.
    <div className="min-h-full text-foreground">
      <div className="settings-page">
        <header className="settings-header">
          <p>SETTINGS · GATOR PASS ACCOUNT</p>
          <h1>Your account.</h1>
          <p className="settings-sub">The Gator Pass identity you use across the field board, Gatorize Me and the hosted server.</p>
        </header>

        <section className="settings-card">
          <h2>Identity</h2>
          <div className="settings-identity">
            <Avatar className="h-12 w-12 ring-1 ring-inset ring-border">
              <AvatarImage src={user?.imageUrl ?? undefined} referrerPolicy="no-referrer" />
              <AvatarFallback className="text-sm">{(user?.name?.[0] ?? user?.email?.[0] ?? '?').toUpperCase()}</AvatarFallback>
            </Avatar>
            <div>
              <strong>{user?.name ?? 'Signed in'}</strong>
              <span>{user?.email ?? '—'}</span>
            </div>
          </div>
          <ul className="settings-rows">
            <li><span className="settings-label">Name</span><span className="settings-value">{user?.name ?? '—'}</span></li>
            <li><span className="settings-label">Email</span><span className="settings-value">{user?.email ?? '—'}</span></li>
          </ul>
          <Button variant="secondary" className="settings-signout" onClick={() => signOut()}>
            Sign out
          </Button>
        </section>
      </div>
    </div>
  )
}
