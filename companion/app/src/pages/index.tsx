/**
 * Static title screen for the native Super Gatorlator 64 campus adventure.
 * Keep it renderable without browser APIs so the page can be prerendered.
 */

import { Link } from 'react-router-dom'
import { ArrowDown, ArrowUpRight, Building2, Gamepad2, Users } from 'lucide-react'
import { Seo } from '../components/Seo'
import { SiteHeader } from '../components/SiteHeader'
import { APP_NAME } from '../constants'
import { seo } from '../seo'

function CampusScene() {
  return <div className="game-scene campus-scene" role="img" aria-label="Campus map showing the two enterable game interiors: Reitz Union and Marston Library">
    <img className="scene-map" src="/campus-map-overview.jpg" alt="" />
    <div className="scene-map-wash" />
    <div className="scene-map-header"><span><Gamepad2 size={15}/> LEVEL SELECT · UF CAMPUS</span><b>02 PLAYABLE INTERIORS</b></div>
    <div className="scene-map-footer"><strong>7 CAMPUS MISSIONS</strong><span>OUTDOOR EXTERIORS · CO-OP CHALLENGES</span></div>
    <small className="scene-map-credit">MAP © OPENSTREETMAP CONTRIBUTORS</small>
  </div>
}

export default function Landing() {
  return <>
    <Seo {...seo} path="/" />
    <SiteHeader />
    <div data-testid="static-landing" className="landing-shell game-landing">
      <main>
        <section className="game-title-screen" aria-labelledby="game-title">
          <div className="title-copy">
            <p className="eyebrow title-eyebrow"><span className="pixel-caret">▶</span> PRESS START · GAINESVILLE, FL</p>
            <h1 id="game-title"><span>SUPER</span><span>GATORLATOR <i>64</i></span></h1>
            <p className="title-description">A campus-sized platform adventure. Team up, explore the Reitz and Marston, and take on the challenges tucked inside.</p>
            <div className="title-actions"><Link to="/home" className="primary-action start-button"><Gamepad2 size={19}/> OPEN THE MISSION BOARD <ArrowUpRight size={17}/></Link><span className="native-note"><span className="note-dot"/> PLAYED IN SM64COOPDX</span></div>
          </div>
          <CampusScene />
          <div className="screen-corner corner-left">PLAYER 01 <span>●</span></div>
          <a className="scroll-cue" href="#level-select"><ArrowDown size={14}/> SCROLL TO LEVEL SELECT</a>
        </section>

        <section id="level-select" className="level-select-section" aria-labelledby="level-title">
          <div className="section-heading game-section-heading"><div><p className="section-index"><span>CAMPUS LEVEL SELECT</span> · 02 ENTERABLE INTERIORS · 07 MISSIONS</p><h2 id="level-title">Choose your next mission</h2></div></div>
          <div className="world-stop-grid">
            <article className="world-stop reitz-stop"><div className="stop-illustration stage-token"><span>WORLD 01</span><Building2 size={35}/><b>REITZ</b></div><div className="stop-copy"><span className="stop-kicker">REITZ UNION INTERIOR · ENGINEERING EXTERIOR</span><h3>Reitz & Engineering</h3><p>Climb the Union, collect meal-swipe tokens, or work the robotics crane together.</p><span className="mission-count">3 MISSIONS <span>·</span> 1 CO-OP</span></div></article>
            <article className="world-stop marston-stop"><div className="stop-illustration stage-token marston-token"><span>WORLD 02</span><Building2 size={35}/><b>MARSTON</b></div><div className="stop-copy"><span className="stop-kicker">MARSTON SCIENCE LIBRARY</span><h3>Marston Library</h3><p>Climb the atrium, find lost textbooks, or book a study room with a teammate.</p><span className="mission-count">3 MISSIONS <span>·</span> 1 CO-OP</span></div></article>
          </div>
          <div className="level-select-footer"><span>2 ENTERABLE BUILDINGS</span><span>7 CAMPUS MISSIONS</span><Link to="/home">OPEN MISSION BOARD <ArrowUpRight size={14}/></Link></div>
        </section>


        <section className="featured-coop" aria-label="Featured co-op mission"><div className="coop-emblem"><Users size={25}/><span>2P</span></div><div className="coop-copy"><span>FEATURED CO-OP MISSION</span><h2>Two players. One robotics lab.</h2><p>One teammate steers the crane. The other rides up and hits the sensor gates. Talk it out and make the climb.</p></div><Link to="/home" className="coop-link">VIEW MISSION BOARD <ArrowUpRight size={15}/></Link><div className="coop-dots" aria-hidden="true">··························</div></section>
      </main>

      <section className="how-it-works game-how" aria-labelledby="how-it-works"><div className="how-title"><p className="eyebrow">MAKE YOUR GATOR · JOIN THE ADVENTURE</p><h2 id="how-it-works">Your look.<br/><em>Your player.</em></h2></div><div className="how-copy"><p>Turn a few photos into a playable, low-poly campus character. A private Vultr GPU runs a local vision model to build a character spec; Blender turns it into textures, animations, and an in-game gator.</p><div className="game-pipeline"><span>YOUR PHOTOS</span><i>→</i><span>GATOR BUILDER</span><i>→</i><span>SM64 CO-OP</span></div><Link to="/gatorize" className="builder-link">MAKE YOUR GATOR <ArrowUpRight size={14}/></Link></div></section>

      <footer className="landing-footer game-footer"><span>SUPER GATORLATOR 64 · UF</span><span>ONE CAMPUS · MANY WAYS UP</span><span>IN-GAME RECORDS · BUILT FOR CO-OP</span></footer>
    </div>
  </>
}
