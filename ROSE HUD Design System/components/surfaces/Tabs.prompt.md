Tracked-caps tab row; `line` has a glowing red underline that glides (480ms ease-out), `chips` matches the top-right mode chips.

```jsx
<Tabs value={tab} onChange={setTab} items={[{id:'brief',label:'Brief'},{id:'data',label:'Data',count:4},{id:'sources',label:'Sources'}]} />
<Tabs variant="chips" value={mode} onChange={setMode} items={['History','Text','Camera']} />
```
