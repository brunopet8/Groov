The floating HUD panel — this system's card; use for every research brief, chart, stat or media block.

```jsx
<Panel eyebrow="Source · The Verge" meta="#A-112" onClose={close}
  title="Meta Quest 3S / Quest 3 — shipping">
  <p style={{ margin: 0, font: 'var(--type-body-sm)', color: 'var(--fg-2)' }}>…</p>
</Panel>
```

- Hover: border → red 40%, brackets grow red, radial light follows cursor.
- `active` — permanently lit (the panel GROOV is currently talking about).
- `delay` — stagger enter animations by 40–60ms per panel.
- `interactive={false}` for static/print contexts.
