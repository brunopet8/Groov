Small notification panel (bottom-left stack) for system events — new panel spawned, source failed, mic muted.

```jsx
<Toast icon="radio" title="Listening" message="Say a topic to research." tone="rose" duration={4000} onClose={…} />
<Toast icon="triangle-alert" title="Source failed" message="theverge.com timed out." tone="red" onClose={…} />
```

- `duration` drains a 1px line along the bottom, then calls `onClose`.
- Stack with `display:flex; flex-direction:column; gap:8px`.
