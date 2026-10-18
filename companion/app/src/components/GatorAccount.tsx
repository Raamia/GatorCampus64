import { useState } from 'react'
import { api, login } from '../lib/gator-api'

export default function GatorAccount({ onDeleted }: { onDeleted: () => void }) {
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirmation, setConfirmation] = useState('')

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true); setMessage('')
    try { await action(); setMessage(success) }
    catch (error) { setMessage((error as Error).message) }
    finally { setBusy(false) }
  }

  return <section className="settings-card">
    <h2>Manage your account</h2>
    <div className="mt-4 space-y-4 text-sm">
      <button disabled={busy} className="underline" onClick={() => void run(
        () => api('/links', { method: 'DELETE' }), 'Game logins revoked. Existing leaderboard results are preserved.',
      )}>Revoke game logins</button>
      <p>Deleting removes your Gator characters, photos and associated leaderboard runs, including shared runs. Linked offline results are removed too. This deletes your game data; your sign-in account stays available. Cleanup may take a few minutes.</p>
      <label className="block">Type DELETE to confirm
        <input aria-label="Confirm account deletion" value={confirmation} onChange={e => setConfirmation(e.target.value)} className="ml-3 rounded border bg-background px-3 py-2" />
      </label>
      <button disabled={busy || confirmation !== 'DELETE'} className="text-destructive underline disabled:opacity-50" onClick={() => void run(async () => {
        await api('/account', { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: 'DELETE' }) })
        onDeleted(); setConfirmation('')
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
  </section>
}
