import * as React from 'react';

/** 280px notification panel that rises in; optional timer line drains along the bottom edge. */
export interface ToastProps {
  /** Tracked caps headline. */
  title?: React.ReactNode;
  message?: React.ReactNode;
  /** @default "neutral" */
  tone?: 'neutral' | 'red' | 'rose';
  /** Lucide icon name. */
  icon?: string;
  /** Auto-dismiss after ms (calls onClose); 0 = sticky. @default 0 */
  duration?: number;
  onClose?: () => void;
  /** e.g. a small ghost Button. */
  action?: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function Toast(props: ToastProps): JSX.Element;
