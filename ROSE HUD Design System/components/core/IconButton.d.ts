import * as React from 'react';

/** Square icon-only button for toolbars, panel headers and the transcript bar. */
export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Lucide icon name. */
  icon: string;
  /** Accessible label (also the native tooltip). */
  label: string;
  /** 22 / 28 / 34px. @default "md" */
  size?: 'sm' | 'md' | 'lg';
  /** @default "ghost" */
  variant?: 'ghost' | 'outline' | 'solid';
  /** Toggled-on state: red icon, red tint, glow. */
  active?: boolean;
  disabled?: boolean;
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
}
export declare function IconButton(props: IconButtonProps): JSX.Element;
