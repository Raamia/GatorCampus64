---
version: alpha
colors:
  background: "#F0EBD9"
  foreground: "#17362E"
  primary: "#E66A3D"
  primaryForeground: "#FFF9EC"
  secondary: "#D9E2A2"
  border: "#C7C5AA"
  muted: "#E4E0CF"
  mutedForeground: "#66736A"
  card: "#FAF7EC"
  dark: "#17362E"
typography:
  display:
    fontFamily: "Impact, Haettenschweiler, 'Arial Narrow Bold', sans-serif"
  sans:
    fontFamily: "'Avenir Next', Avenir, 'Segoe UI', sans-serif"
  mono:
    fontFamily: "'SFMono-Regular', Consolas, monospace"
rounded:
  sm: "0.35rem"
  md: "0.7rem"
  lg: "1rem"
spacing:
  unit: "0.25rem"
components:
  mission-card:
    radius: "0.7rem"
    border: "1px solid #C7C5AA"
  action-button:
    radius: "0.35rem"
    height: "2.75rem"
---

## Overview

This is the **Super Gatorlator 64 game companion**, for teammates organizing around the native SM64CoopDX campus adventure. The game is the product; this site helps players choose a mission, invite a squad, and log player-reported results. It should feel like a campus level-select map: warm paper, dark green ink, and orange route lines linking Reitz, Marston, and the stadium.

This is a companion for students at a laptop or phone during a co-op session. Name Super Gatorlator 64 and identify it as a native 3D game in the first screen. Make clear that the game runs in SM64CoopDX and that results in this web app are player-reported. Keep exact mission names and stage details visible and quick to scan while someone is playing.

Avoid generic SaaS dashboards, sponsor logo walls, neon hacker themes, and decorative game screenshots that do not help a player choose the next action.

## Colors

Paper and warm-white panels provide a calm reading field. Deep green carries primary text and the app shell. Orange is reserved for the next action and active route marker. Pale chartreuse marks co-op readiness. Muted gray-green is supporting text. Success and warning states use text labels as well as color.

The base theme remains light for readability in event spaces. Error, offline, and loading states use the same footprint as their resolved states.

## Typography

Use the condensed display face for short stage headings and the squad code only. Use the sans face for objectives, forms, and results. Use the monospaced face for squad codes, elapsed times, and status metadata. Do not set long paragraphs in the display face.

## Layout

At desktop widths, place a slim identity rail beside a broad mission board, with the run recap in a narrower right column. On mobile, stack the mission, squad actions, and recap in that order. Keep the main action visible without a dense top navigation.

Use generous space around the mission objective and compact spacing for event history. Cards follow the route line only where that line shows progression; do not use numbered decoration without sequence meaning.

## Elevation & Depth

Use paper contrast and thin borders to separate panels. Keep shadows short and quiet. The route line may sit above the paper texture as a single flat graphic.

## Shapes

Use lightly rounded panels and firmer corners on buttons, like labels clipped to a field board. Pills are reserved for connection and mission status.

## Components

Buttons use orange for committed actions and outlined green for secondary actions. Forms use native text and numeric inputs with explicit labels and inline error text. Mission cards show the verified title, objective, player requirement, and authored static hint. Player-reported outcomes carry a persistent visible label.

## Do's and Don'ts

- Keep mission copy exact to the game registry; keep hints tied to authored mission behavior.
- Keep squad codes readable and private to the sharing flow; do not place them in analytics payloads.
- Use short transitions on state changes and respect reduced motion.
- Do not imply game telemetry is automatic or independently verified.
- Do not use full names or free-form chat in event storage.

## Runtime token mapping

The palette maps to the default `@theme` block in `src/styles.css`. `src/themes.css` owns named theme overrides. The mission route illustration is a UI component in `src/pages/(app)/home.tsx`; it uses the same color tokens and does not introduce an independent theme.
