import * as React from 'react';

/** Big light-weight mono number readout ("≈20m") that counts up on mount. */
export interface StatProps {
  /** Number counts up from 0; strings render as-is. */
  value: number | string;
  /** e.g. "≈", "+", "$". */
  prefix?: string;
  /** Unit at 55% size, e.g. "m", "%", "h". */
  suffix?: string;
  /** Micro caps label above. */
  label?: React.ReactNode;
  /** Small body text below. */
  caption?: React.ReactNode;
  /** sm 24 · md 32 · lg 44. @default "md" */
  size?: 'sm' | 'md' | 'lg';
  /** @default "white" */
  tone?: 'white' | 'red';
  /** @default 0 */
  decimals?: number;
  /** Count-up animation. @default true */
  animate?: boolean;
  /** @default "left" */
  align?: 'left' | 'center';
  style?: React.CSSProperties;
}
export declare function Stat(props: StatProps): JSX.Element;
