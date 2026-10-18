import { useEffect, useState } from 'react'
import { getAuthToken, useAuth } from 'deepspace'
import { api, login, token } from '../lib/gator-api'

export default function GatorAccount({ onDeleted }: { onDeleted: () => void }) {
  const { isSignedIn } = useAuth()
  const [linked, setLinked] = useState<boolean | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirmation, setConfirmation] = useState('')

  async function identity(action: 'link' | 'unlink' | 'status') {
    const response = await fetch('/api/account/identity', {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${await getAuthToken()}` },
      body: JSON.stringify({ action, gatorToken: await token() }),
    })
    const body = await response.json() as { linked?: boolean; conflict?: boolean; detail?: string }
    if (!response.ok) throw new Error(body.detail ?? 'Account linking is unavailable.')
    setLinked(Boolean(body.linked))
    if (body.conflict) setMessage('One of these accounts is already linked to a different account. Sign in to that pair to unlink it first.')
  }

  useEffect(() => {
    setLinked(null)
    if (isSignedIn) void identity('status').catch(() => undefined)
  }, [isSignedIn])

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true); setMessage('')
    try { await action(); setMessage(success) }
    catch (error) { setMessage((error as Error).message) }
    finally { setBusy(false) }
  }

  return <details className="gator-card mb-5">
    <summary className="cursor-pointer font-semibold">Account settings</summary>
    <div className="mt-4 space-y-4 text-sm">
      <p>Gator Pass and Field Board have separate sign-ins. Linking connects the two accounts you are signed into now.</p>
      {isSignedIn ? <div className="flex flex-wrap gap-4">
        <span>{linked ? 'Field Board linked' : 'Field Board not linked to this Gator Pass'}</span>
        <button disabled={busy} className="underline" onClick={() => void run(
          () => identity(linked ? 'unlink' : 'link'), linked ? 'Accounts unlinked. Existing data is preserved.' : 'Accounts linked.',
        )}>{linked ? 'Unlink accounts' : 'Link these accounts'}</button>
      </div> : <p>Sign in to Field Board using the site navigation to link it.</p>}
      <button disabled={busy} className="underline" onClick={() => void run(
        () => api('/links', { method: 'DELETE' }), 'Game logins revoked. Existing leaderboard results are preserved.',
      )}>Revoke game logins</button>
      <p>Deleting removes your Gator characters, photos and associated leaderboard runs, including shared runs. Linked offline results are removed too. Your Auth0 and DeepSpace accounts stay intact. Cleanup may take a few minutes.</p>
      <label className="block">Type DELETE to confirm
        <input aria-label="Confirm account deletion" value={confirmation} onChange={e => setConfirmation(e.target.value)} className="ml-3 rounded border bg-background px-3 py-2" />
      </label>
      <button disabled={busy || confirmation !== 'DELETE'} className="text-destructive underline disabled:opacity-50" onClick={() => void run(async () => {
        await api('/account', { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: 'DELETE' }) })
        onDeleted(); setConfirmation(''); setLinked(false)
      }, 'Gator account deleted. Storage and leaderboard cleanup is queued.')}>Delete Gator account</button>
      <p>Deletion requires a recent sign-in. To start over after deletion, sign in again and explicitly register a new Gator account.</p>
      <div className="flex flex-wrap gap-4">
        <button disabled={busy} className="underline" onClick={() => void run(() => login(true), '')}>Sign in again</button>
        <button disabled={busy} className="underline" onClick={() => void run(
          () => api('/account/register', { method: 'POST' }), 'Gator account registered. Previous data stays deleted.',
        )}>Register a new Gator account</button>
      </div>
      {message && <p role="status">{message}</p>}
    </div>
  </details>
}
