Minimal bar chart for research panels; white bars, the key bar red, hover any bar to light it and read its value.

```jsx
<BarChart height={72} data={[{label:'Q1',value:12},{label:'Q2',value:4},{label:'Q3',value:9},{label:'Q4',value:20}]} />
<BarChart highlight={2} showValues unit="m" data={…} />
```

- No gridlines, no axes beyond the 1px baseline.
- Bars grow in with 60ms stagger over 900ms.
