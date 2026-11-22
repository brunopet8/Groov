import * as React from 'react';

/** Micro caps label on hover/focus with a red hairline border. */
export interface TooltipProps {
  content: React.ReactNode;
  /** @default "top" */
  placement?: 'top' | 'bottom' | 'left' | 'right';
  /** Hover delay in ms. @default 120 */
  delay?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function Tooltip(props: TooltipProps): JSX.Element;
