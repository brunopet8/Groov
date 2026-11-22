Square icon-only button for toolbars, panel headers (close ×) and the transcript bar (mic, camera).

```jsx
<IconButton icon="x" label="Close" size="sm" />
<IconButton icon="mic" label="Mute" variant="outline" active={listening} />
<IconButton icon="send" label="Send" variant="solid" />
```

- `variant` — `ghost` (default) · `outline` · `solid` (red).
- `active` — toggled state: red icon + tint + glow.
- Always pass `label`.
