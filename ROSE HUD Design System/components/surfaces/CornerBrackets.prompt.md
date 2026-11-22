Four L-shaped corner ticks that frame any box; the system's signature motif — use on panels, viewports, focused fields, hovered buttons.

```jsx
<div style={{ position: 'relative', border: '1px solid var(--border-subtle)' }}>
  <CornerBrackets active={hovered} />
  …
</div>
```

- `active` — grows ticks 8→14px, turns them red with glow. Animates with `--ease-out`.
- `offset={-1}` sits the ticks on a 1px border; use positive values to float them inside.
- Parent must be `position: relative`.
