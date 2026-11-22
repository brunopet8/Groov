20px tracked-caps chip; use for the top-right mode chips, filters and topic tags.

```jsx
<Tag selected onClick={…}>History</Tag>
<Tag onClick={…}>Camera</Tag>
<Tag icon="cpu" onRemove={…}>Meta Quest</Tag>
```

- `selected` — red border, red tint, faint glow.
- `onClick` makes it a keyboard-accessible toggle; `onRemove` adds a ×.
