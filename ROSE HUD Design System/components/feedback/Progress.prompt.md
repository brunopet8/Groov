Boot-style progress bar with process label and % readout; use for boot, loading modules, long research jobs.

```jsx
<Progress label="Carregando módulos..." value={47} width={260} />
<Progress size="sm" value={72} showValue={false} />
<Progress indeterminate tone="rose" />
```

- Fill eases over 900ms; a soft highlight travels along it continuously.
- Label is centered tracked caps ending in "...".
