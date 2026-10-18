import { Link } from 'react-router-dom'
import { useGatorSession } from '../lib/gator-session'
import { GatorSignIn } from './GatorSignIn'

export function GatorNavAccount() {
  const session = useGatorSession()
  return session.signedIn
    ? <Link to="/settings" className="app-nav-signin" aria-label="Account settings"><span data-testid="nav-user-name" className="max-w-24 truncate">{session.name ?? 'Account'}</span></Link>
    : <GatorSignIn compact />
}
