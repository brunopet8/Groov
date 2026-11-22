import * as React from 'react';

/**
 * Tracked-caps action button. Primary is solid red with cursor-following light and a hover sweep;
 * secondary is a hairline that grows red corner brackets on hover.
 */
export interface ButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'type'> {
  children?: React.ReactNode;
  /** @default "primary" */
  variant?: 'primary' | 'secondary' | 'ghost' | 'rose';
  /** sm 22px · md 28px · lg 34px. @default "md" */
  size?: 'sm' | 'md' | 'lg';
  /** Lucide icon name before the label. */
  icon?: string;
  /** Lucide icon name after the label. */
  iconRight?: string;
  disabled?: boolean;
  fullWidth?: boolean;
  type?: 'button' | 'submit' | 'reset';
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
}
export declare function Button(props: ButtonProps): JSX.Element;
