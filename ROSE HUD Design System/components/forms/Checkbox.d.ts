import * as React from 'react';

/** 12px square check; checked = red fill + glow, check mark springs in. */
export interface CheckboxProps {
  /** Controlled value. */
  checked?: boolean;
  defaultChecked?: boolean;
  onChange?: (checked: boolean) => void;
  label?: React.ReactNode;
  disabled?: boolean;
  style?: React.CSSProperties;
}
export declare function Checkbox(props: CheckboxProps): JSX.Element;
