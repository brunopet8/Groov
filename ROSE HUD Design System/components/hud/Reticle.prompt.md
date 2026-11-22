The animated GROOV orb/core — ringed reticle with a breathing red arc pair; use as the assistant presence (corner orb, boot center, listening state). `view="3d"` turns it into a tilting gyroscope.

```jsx
<Reticle size={200} state="online" view="3d" ringText="GROOV // CORE 01">
  <span style={{ font: 'var(--type-display)', letterSpacing: '.06em' }}>GROOV</span>
</Reticle>
<Reticle size={72} state="listening" tone="rose" ticks={false} />
```

- `state` drives speed: off (still, gray) · idle/online · listening (+ sonar) · thinking (fast).
- `view="3d"` — perspective tilt, layers separated in depth, two gyroscope rings spinning on X/Y, continuous wobble, pointer tilt. Switch between views to animate the tilt.
- `tone="rose"` for the hot-pink rim.
- Children stay flat and readable in both views.
