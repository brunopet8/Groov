import * as React from 'react';

/**
 * Sunken black text field. Focus ignites red corner brackets and an inner red glow; caret is red.
 */
export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** Micro caps label above. */
  label?: string;
  /** Helper line below. */
  hint?: string;
  /** Error line below; turns the frame red. */
  error?: string;
  /** Leading Lucide icon. */
  icon?: string;
  /** Trailing micro text (unit, shortcut). */
  suffix?: string;
  /** 22 / 28 / 34px. @default "md" */
  size?: 'sm' | 'md' | 'lg';
  /** Use JetBrains Mono for the value. */
  mono?: boolean;
  disabled?: boolean;
  inputStyle?: React.CSSProperties;
}
export declare function Input(props: InputProps): JSX.Element;
