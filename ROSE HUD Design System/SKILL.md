---
name: groov-hud-design
description: Use this skill to generate well-branded interfaces and assets for GROOV HUD, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the readme.md file within this skill, and explore the other available files.
If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.
If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

Quick rules: black/gray ground (`--bg-page`), white text (`--fg-1`), red is the only main color (`--accent`), rosé for fine detail (`--rose`). Small type — 12px body, 10px tracked caps labels. Sharp corners, 1px hairlines, corner brackets, glow instead of shadow. Everything animates with `--ease-out`; hover ignites color. Link `styles.css`; components live in `components/` (React, CSS variables only).
