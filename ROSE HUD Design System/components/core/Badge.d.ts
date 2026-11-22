import * as React from 'react';

/** Tiny 16px mono label for counts, versions and states inside panels. */
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  children?: React.ReactNode;
  /** @default "neutral" */
  tone?: 'neutral' | 'red' | 'rose' | 'white';
  /** @default "soft" */
  variant?: 'soft' | 'solid' | 'outline';
  /** Leading glowing dot. */
  dot?: boolean;
}
export declare function Badge(props: BadgeProps): JSX.Element;
