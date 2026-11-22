import * as React from 'react';

/** Mono caps dropdown with a blurred ink menu; selected option marked with a glowing red dot. */
export interface SelectOption { value: string; label: string; }
export interface SelectProps {
  /** Strings or {value,label}. */
  options: Array<string | SelectOption>;
  value?: string;
  onChange?: (value: string) => void;
  /** @default "Select" */
  placeholder?: string;
  label?: string;
  /** @default "md" */
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  width?: number | string;
  style?: React.CSSProperties;
}
export declare function Select(props: SelectProps): JSX.Element;
