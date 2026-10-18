---
version: alpha
colors:
  background: "#EAF1FB"
  foreground: "#152B4F"
  primary: "#F07828"
  primaryForeground: "#152B4F"
  secondary: "#F9CD4D"
  border: "#B7CBE3"
  muted: "#DEE8F7"
  mutedForeground: "#526987"
  card: "#FFFAF0"
  dark: "#152B4F"
typography:
  display:
    fontFamily: "Impact, 'Arial Black', 'Trebuchet MS', sans-serif"
  sans:
    fontFamily: "'Trebuchet MS', ui-sans-serif, system-ui, sans-serif"
  mono:
    fontFamily: "'SFMono-Regular', Consolas, monospace"
rounded:
  sm: "0.3rem"
  md: "0.45rem"
  lg: "0.7rem"
spacing:
  unit: "0.25rem"
components:
  mission-card:
    rounded: "0.45rem"
    backgroundColor: "#FFFAF0"
    textColor: "#152B4F"
    padding: "1rem"
  action-button:
    rounded: "0.3rem"
    backgroundColor: "#F07828"
    textColor: "#152B4F"
    height: "2.75rem"
---

## Overview

The **GatorCampus 64 companion** should feel like the level-select and mission boards from a bright 1990s 3D platform game, translated into a useful campus companion. The game is the product; this site helps players choose a mission and see their recorded results. Name GatorCampus 64 and identify it as a native 3D game in the first screen. Make clear that the game runs in SM64CoopDX; results shown here come from the hosted server (verified, via Gator Pass `/login`) or are synced from a player's own game (offline, unverified).

Its signature is a sky-blue campus field framed in stadium navy, with Gator-orange route markers and warm gold highlights. The landing page should feel like a platform-game title screen: original low-poly campus scenery, a custom gator avatar and crest pickup, a readable mission HUD, and an accurate campus map. Product routes carry the same world through game-menu navigation, a mission board, score screen, and field manual. Use playful, chunky display type and game-menu framing for key actions. The visual reference is an N64-era campus level-select screen; do not use Mario logos, character art, coins, stars, or other borrowed game assets.

Avoid generic SaaS dashboards, sponsor logo walls, neon hacker themes, and decorative game screenshots that do not help a player choose the next action.

## Colors

Sky blue is the page field and route-map surface. Stadium navy carries primary text, navigation, and high-emphasis game panels. Orange marks actions and active routes. Gold is a sparing reward or secondary highlight color. Warm cream panels provide a calm reading field against the blue page. Supporting text uses slate blue. Success and warning states keep their semantic colors and use text labels as well as color.

The palette stays light for readability in event spaces. Dark navy appears as a deliberate panel or callout, not as a full-screen dark theme. Error, offline, and loading states keep the same footprint as resolved states.

## Typography

Use Impact/Arial Black/Trebuchet fallbacks for short, bold stage headings and compact labels. Use the system sans stack for objectives, forms, and results. Use the monospaced face for elapsed times and status metadata. Keep long paragraphs in the sans face and preserve readable mixed-script fallbacks.

## Layout

The companion home leads with a hero naming the game and summarizing the mission board, then lists the campus missions grouped by location, then a record-chase panel linking to the leaderboard. Keep the native-game handoff clear and make launch instructions one click away. Stack sections single-column on mobile. Keep the main action visible without a dense top navigation.

Use the repository's true-scale UF campus map as the backdrop, with pins on Reitz & Engineering and Marston Library. Featured mission locations do not represent every enterable building on the map. Do not display a total count of enterable interiors or buildings. Keep each building's mission list in a separate card so labels on the real map remain legible. Do not draw an invented route or imply these are adjacent sequential stages.

## Elevation & Depth

Use flat blue fields, warm cream panels, thin blue borders, and short navy offset shadows that echo a game menu's crisp edges. The route line may sit above a subtle map grid as a single flat graphic.

## Shapes

Use compact rounded panels and firm corners on buttons, like labels clipped to a field board. Pills are reserved for connection and mission status. Use stripes or pixel-like geometry sparingly as framing, not as decoration behind long text.

## Components

Buttons use orange for committed actions, blue focus rings, and outlined navy or blue for secondary actions. Forms use native text and numeric inputs with explicit labels and inline error text. Mission cards show the verified title, objective, player requirement, and authored static hint. Player-reported outcomes carry a persistent visible label.

## Do's and Don'ts

- Keep mission copy exact to the game registry; keep hints tied to authored mission behavior.
- Use short transitions on state changes and respect reduced motion.
- Do not imply game telemetry is automatic or independently verified.
- Do not use full names or free-form chat in event storage.
- Do not copy Mario branding or recognizable Mario assets; communicate the genre through color, geometry, and playful display type.

## Runtime token mapping

The runtime theme is canonical. `src/themes.css` sets semantic variables for the `field` theme and game aliases, `src/styles.css` maps those values into Tailwind and site components, `src/themes.ts` supplies theme metadata, and `index.html` matches the first-paint background. Keep those files aligned with this palette.

## Shared header and minigames

Use the navy game-menu header across the landing page and application routes: a gold G crest with orange edging, cream brand text, readable Trebuchet navigation, and a warm gold primary or current-route tile. Other navigation links use navy outlined buttons. SiteHeader owns the same route list, layout, active states, and mobile menu on every page. Navigation adds the authenticated account controls on data-backed pages.

Gator Chomp Chorus belongs with the location-grouped mission entries under The Swamp, Act 3, alongside the campus challenges. Do not give one minigame its own section on the Play setup page; reserve that page for installation, server connection, account linking, and concise directions to find activities in game. Keep the six Reitz/Marston challenges grouped by building. Solo grades do not imply a verified leaderboard time.
