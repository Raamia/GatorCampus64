import { ArrowUpRight, Copy, ExternalLink, Gamepad2, MapPin, QrCode, Smartphone, Wrench } from 'lucide-react'
import { useState } from 'react'

const ADDRESS = 'play.gatorcamp.us:7777'

const steps = [
  {
    icon: Wrench,
    title: 'Install sm64coopdx',
    body: <>Download <strong><a href="https://github.com/coop-deluxe/sm64coopdx/releases" target="_blank" rel="noreferrer">sm64coopdx v1.5.1 <ExternalLink size={12} className="play-step-link-icon" /></a></strong> and launch it once with your own US Super Mario 64 ROM (not included).</>,
  },
  {
    icon: Gamepad2,
    title: 'Direct connect',
    body: <>Choose <strong>Join → Direct Connect</strong>, then enter <code>play.gatorcamp.us</code> on port <code>7777</code>.</>,
  },
  {
    icon: QrCode,
    title: 'Link Gator Pass',
    body: <>Type <code>/login</code> in game and scan the QR code — or enter the device code — with your phone.</>,
  },
  {
    icon: Smartphone,
    title: 'Pick your gator',
    body: <>Approve on your phone and your built gator is selected for you. Your name tag gets a star.</>,
  },
]

export default function PlayPage() {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(ADDRESS)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }
  return <main className="play-page">
    <header className="play-hero">
      <div className="play-hero-copy">
        <p className="play-kicker"><Gamepad2 size={15}/> GAME SETUP · SM64COOPDX</p>
        <h1>Step into<br /><em>the campus.</em></h1>
        <p className="play-sub">GatorCampus 64 is a native co-op game. Install sm64coopdx, connect to the campus server, then bring your Gator Pass character into Reitz and Marston.</p>
        <div className="play-location"><MapPin size={14}/> GAINESVILLE, FLORIDA <span>·</span> 2 BUILDINGS <span>·</span> 7 MISSIONS</div>
      </div>
    </header>
    <div className="play-layout">
      <section className="play-instructions" aria-labelledby="play-steps-title">
        <div className="play-section-heading"><p>FROM DESKTOP TO CAMPUS</p><h2 id="play-steps-title">Get into the game</h2></div>
        <ol className="play-steps">
        {steps.map((step, i) => <li key={step.title} className="play-step">
          <span className="play-step-n">{String(i + 1).padStart(2, '0')}</span>
          <step.icon size={18} className="play-step-icon" aria-hidden />
          <div><h3>{step.title}</h3><p>{step.body}</p></div>
        </li>)}
        </ol>
      </section>
      <aside className="play-server">
        <span className="play-server-label">JOIN THE CAMPUS SERVER</span>
        <h2>Join a co-op session.</h2>
        <p>Choose <strong>Join → Direct Connect</strong> in sm64coopdx, then use this address.</p>
        <code className="play-server-address">{ADDRESS}</code>
        <button className="play-copy" onClick={() => void copy()}><Copy size={15} />{copied ? 'Copied to clipboard' : 'Copy server address'}<ArrowUpRight size={14}/></button>
        <a className="play-guide" href="https://gatorcamp.us" target="_blank" rel="noreferrer">Full game guide <ExternalLink size={13} /></a>
      </aside>
    </div>
  </main>
}
