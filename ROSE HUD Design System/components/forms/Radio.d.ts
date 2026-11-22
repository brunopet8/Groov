import * as React from 'react';

/** Radio group; selected dot springs in red with glow. */
export interface RadioOption { value: string; label: string; }
export interface RadioProps {
  options: Array<string | RadioOption>;
  /** Controlled value. */
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  /** Group aria-label. */
  name?: string;
  /** @default "column" */
  direction?: 'row' | 'column';
  disabled?: boolean;
  style?: React.CSSProperties;
}
export declare function Radio(props: RadioProps): JSX.Element;
