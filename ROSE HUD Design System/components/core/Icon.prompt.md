Lucide icon (CDN substitute for the missing brand set), masked so it takes `currentColor`; use inside buttons, chips, toolbars.

```jsx
<Icon name="mic" size={14} />
<Icon name="x" color="var(--red-400)" />
```

- `name` — any Lucide name (kebab-case).
- `size` — 12 (controls) / 14 (toolbars). Never above 20.
- Prefer text labels; icons are secondary in this system.
