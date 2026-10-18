import { useEffect, useState, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Activity, Footprints, Gamepad2, House, Menu, Settings, Trophy, X } from 'lucide-react'
import { APP_NAME } from '../constants'
import { nav, type NavItem } from '../nav'

const publicItems = nav.filter((item) => (!item.devOnly || import.meta.env.DEV) && !item.roles)

/** One header for both the prerendered landing and the data-backed routes. */
export function SiteHeader({ items = publicItems, account }: { items?: NavItem[]; account?: ReactNode }) {
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => { setMenuOpen(false) }, [pathname])

  return <nav data-testid="app-navigation" aria-label="Main navigation" className={`app-nav ${menuOpen ? 'menu-open' : ''}`}>
    <div className="app-nav-inner">
      <Link to="/" className="app-nav-brand" aria-label={`${APP_NAME} home`}>
        <span className="app-nav-crest" aria-hidden="true">G</span>
        <span><strong>SUPER GATORLATOR 64</strong><small>UNIVERSITY OF FLORIDA · CO-OP ADVENTURE</small></span>
      </Link>
      <div className="app-nav-links" id="site-navigation-links">{items.map((item) => {
        const active = pathname === item.path || pathname.startsWith(`${item.path}/`)
        const Icon = item.path === '/leaderboard' ? Trophy : item.path === '/gatorize' ? Footprints
          : item.path === '/pipeline' ? Activity : item.path === '/play' ? Gamepad2 : item.path === '/settings' ? Settings : House
        return <Link key={item.path} to={item.path} aria-current={active ? 'page' : undefined} className={`app-nav-link${active ? ' is-active' : ''}`}>
          <Icon size={15} aria-hidden/>{item.label}
        </Link>
      })}</div>
      {account === undefined ? <Link to="/settings" data-testid="nav-sign-in-button" className="app-nav-signin">Sign in</Link> : account}
      <button className="app-nav-mobile-toggle" onClick={() => setMenuOpen((open) => !open)} aria-label="Toggle menu" aria-expanded={menuOpen} aria-controls="site-navigation-links">
        {menuOpen ? <X size={16} aria-hidden/> : <Menu size={16} aria-hidden/>}
      </button>
    </div>
  </nav>
}
