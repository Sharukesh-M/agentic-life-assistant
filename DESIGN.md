# JARVIX Design & Visual Language Specification

This document governs the design system, visual aesthetics, component standards, and accessibility rules for **JARVIX – Goal-Aware Proactive Agentic AI Life Assistant**.

## 1. Aesthetic Principles & Design Taste

- **Visual Direction**: Modern, premium, glassmorphism dark-mode interface with vibrant subtle accents (Emerald/Violet/Cyan), high-contrast readability, and micro-animations for dynamic system state changes.
- **Anti-Slop Guidelines**: Follow strict anti-slop principles ([.agents/skills/antislop](file:///Users/sharukeshm/Desktop/1/.agents/skills/antislop/SKILL.md)). Eliminate generic AI templates, unnecessary emoji clutter, bad contrast ratios, and repetitive layout patterns.
- **Typography System**: Modern geometric sans-serif for UI chrome (`Inter` / `Outfit`) and clean monospace (`JetBrains Mono` / `Fira Code`) for tool outputs, status telemetry, and code preview blocks.

## 2. Design Tokens & Standards

Design tokens follow the 3-Tier DTCG Architecture (Primitive → Semantic → Component) referenced in [.agents/skills/design-tokens](file:///Users/sharukeshm/Desktop/1/.agents/skills/design-tokens/SKILL.md):
- **Primitives**: Base color palettes, font scale ratios, standard elevation curves.
- **Semantics**: Contextual mapping (`--color-bg-primary`, `--color-accent-active`, `--color-status-success`, `--color-status-warning`).
- **Components**: Component-specific tokens (`--card-border-radius`, `--modal-shadow-glow`).

## 3. Accessibility & WCAG Compliance

- **Standards Target**: WCAG 2.2 AA (with AAA contrast targets for core text blocks).
- **Interactive Targets**: Minimum 44x44px touch targets with visible focus rings (`:focus-visible`).
- **Screen Reader Support**: Semantic HTML5 elements (`<main>`, `<nav>`, `<aside>`, `<section>`), full ARIA state attributes (`aria-expanded`, `aria-live` for proactive agent notifications).
- **Reduced Motion**: Respect `prefers-reduced-motion` media queries for all agent voice waveforms and task timeline animations.

## 4. Supporting Resources

For complete token collections, brandkit examples, and WCAG audit tools:
- UX/UI Skills: [.agents/skills/](file:///Users/sharukeshm/Desktop/1/.agents/skills)
- Design Systems Reference Library: [references/awesome-design-md](file:///Users/sharukeshm/Desktop/1/references/awesome-design-md)
- Anti-Slop Guidelines: [references/anti-slop](file:///Users/sharukeshm/Desktop/1/references/anti-slop)
