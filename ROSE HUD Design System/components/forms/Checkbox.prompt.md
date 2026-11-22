12px square checkbox; checked is solid red with glow and a check that springs in.

```jsx
<Checkbox label="Show sources" defaultChecked />
<Checkbox checked={pin} onChange={setPin} label="Pin panel" />
```

- Controlled (`checked` + `onChange`) or uncontrolled (`defaultChecked`).
