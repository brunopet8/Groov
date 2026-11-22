import * as React from 'react';

/** Minimal panel bar chart: white bars, the key bar in red, 1px baseline, micro labels. Bars grow in staggered. */
export interface BarDatum { label?: string; value: number; }
export interface BarChartProps {
  data: BarDatum[];
  /** Plot height in px. @default 80 */
  height?: number;
  /** "max", a bar index, or "none". @default "max" */
  highlight?: 'max' | 'none' | number;
  /** Always show values (otherwise on hover). */
  showValues?: boolean;
  /** Appended to values. */
  unit?: string;
  /** @default true */
  animate?: boolean;
  /** Gap between bars in px. @default 6 */
  gap?: number;
  style?: React.CSSProperties;
}
export declare function BarChart(props: BarChartProps): JSX.Element;
