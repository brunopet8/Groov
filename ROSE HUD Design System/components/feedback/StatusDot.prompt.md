Glowing status dot with optional tracked caps label; use for system state, live sources, pager dots.

```jsx
<StatusDot tone="online" label="Online" bracketed />
<StatusDot tone="live" label="Listening" />
<StatusDot tone="idle" />
```

- Tones stay in palette: online/error = red, live = hot rose, warn = rosé, ok = white, idle = gray.
- Hot tones pulse (2.4s); `live` adds a sonar ping.
