Modal confirmation or detail view: blurred scrim + a permanently-lit Panel; use sparingly (destructive actions, settings).

```jsx
<Dialog open={open} onClose={close} eyebrow="System" title="Clear all panels?"
  actions={<><Button variant="ghost" size="sm" onClick={close}>Cancel</Button><Button size="sm">Clear</Button></>}>
  Removes 12 panels from the canvas. Transcript is kept.
</Dialog>
```

- Esc and scrim click call `onClose`.
