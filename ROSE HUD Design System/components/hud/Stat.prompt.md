Big mono number readout that counts up; use one per panel for the headline figure.

```jsx
<Stat label="Quest headsets sold" prefix="≈" value={20} suffix="m" caption="Cumulative, reported early 2025" />
<Stat value={87} suffix="%" tone="red" size="sm" />
```

- Weight 300 mono, tabular numerals, soft glow.
- `tone="red"` only for the single most important number on screen.
