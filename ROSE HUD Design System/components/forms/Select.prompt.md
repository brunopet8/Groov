Mono caps dropdown (like the top-right voice picker); menu fades up, selected option gets a glowing red dot.

```jsx
<Select size="sm" value={voice} onChange={setVoice}
  options={['Groov — warm', 'Groov — neutral', 'Groov — fast']} />
```

- Keyboard: ↑/↓ to move, Enter to pick, Esc to close.
- Options are strings or `{ value, label }`.
