Tracked-caps action button; use `primary` (red) once per view for the main action, `secondary` for everything else.

```jsx
<Button icon="play">Proceed</Button>
<Button variant="secondary" size="sm">Clear text</Button>
<Button variant="ghost" iconRight="arrow-up-right">Open source</Button>
<Button variant="rose">Pin</Button>
```

- `variant` — `primary` red fill + glow + light sweep on hover · `secondary` hairline, red corner brackets on hover · `ghost` text only · `rosé` detail outline.
- `size` — `sm` 22px / `md` 28px / `lg` 34px; label 9/10/11px.
- Light follows the cursor inside the button; press darkens and scales to .98.
