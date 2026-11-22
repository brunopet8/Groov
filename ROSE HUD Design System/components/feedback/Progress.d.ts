import * as React from 'react';

/** Boot-style progress bar: rounded ink track, glowing red fill with a travelling highlight, % readout. */
export interface ProgressProps {
  /** 0–100. Width eases over 900ms. */
  value?: number;
  /** Centered tracked-caps process line above ("CARREGANDO MÓDULOS..."). */
  label?: React.ReactNode;
  /** @default true */
  showValue?: boolean;
  /** sm 2px · md 6px · lg 8px. @default "md" */
  size?: 'sm' | 'md' | 'lg';
  /** @default "red" */
  tone?: 'red' | 'rose' | 'white';
  indeterminate?: boolean;
  width?: number | string;
  style?: React.CSSProperties;
}
export declare function Progress(props: ProgressProps): JSX.Element;
