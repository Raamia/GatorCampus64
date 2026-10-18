/**
 * Landing page — a STATIC page.
 *
 * It lives at the top level of src/pages/ (not under (app)/), so it renders
 * with no DeepSpace providers: no auth session fetch, no records WebSocket.
 * That makes it cheap to serve and safe for logged-out / crawler traffic.
 *
 * Need live data or auth here? Move this file to src/pages/(app)/index.tsx
 * and it becomes a dynamic page. Conversely, any page you want to keep static
 * (marketing, docs, legal) belongs at this top level.
 *
 * Top-level pages are also prerendered to static HTML at build
 * (prerender.ts, via vite.config.ts) so crawlers read real content.
 * Keep them renderable without a browser: no window/document during render,
 * prose in HTML text, reveal animations in CSS keyframes rather than JS-driven
 * initial states. `<Seo>` comes first and reads src/seo.ts.
 */

import { Link } from 'react-router-dom'
import { ArrowUpRight, MapPin } from 'lucide-react'
import { Seo } from '../components/Seo'
import { APP_NAME } from '../constants'
import { seo } from '../seo'

export default function Landing() {
  return (
    <>
      <Seo {...seo} path="/" />
      <div data-testid="static-landing" className="landing-shell">
        <nav className="landing-nav"><Link to="/" className="brand-mark"><span>G</span> GATOR FIELD BOARD</Link><span>SWAMPHACKS XII · UF</span></nav>
        <main className="landing-hero"><div className="landing-copy"><p className="eyebrow"><MapPin size={15}/> UNIVERSITY OF FLORIDA · CAMPUS FIELD BOARD</p><h1>Your campus.<br/><em>Your character.</em></h1><p>Become a playable gator from your photos, meet your friends on campus, and race for the leaderboard.</p><Link to="/gatorize" className="primary-action">Make your gator <ArrowUpRight size={16}/></Link><div className="landing-small">NATIVE CO-OP ADVENTURE <span/> CUSTOM CHARACTERS</div></div><div className="landing-map"><div className="map-grid"/><div className="route route-one"/><div className="route route-two"/><span className="pin pin-a"/><span className="pin pin-b"/><span className="pin pin-c"/><span className="map-label label-a">REITZ UNION</span><span className="map-label label-b">MARSTON</span><span className="map-label label-c">THE QUAD</span><div className="map-caption"><span>FIELD NOTES · 01</span><strong>Two corners<br/>of campus. One<br/>good afternoon.</strong></div></div></main>
        <footer className="landing-footer"><span>GAINESVILLE, FL</span><span>ONE CAMPUS · MANY WAYS UP</span><span>{APP_NAME.toUpperCase()}</span></footer>
      </div>
    </>
  )
}
