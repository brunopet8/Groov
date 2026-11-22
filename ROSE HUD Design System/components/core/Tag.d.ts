import * as React from 'react';

/** 20px tracked-caps chip — the top-right mode tabs (HISTORY · TEXT · CLEAR TEXT · CAMERA), filters, topics. */
export interface TagProps extends React.HTMLAttributes<HTMLSpanElement> {
  children?: React.ReactNode;
  /** Red border + tint + glow. */
  selected?: boolean;
  /** Makes the chip a toggle button. */
  onClick?: (e: React.SyntheticEvent) => void;
  /** Shows a trailing × that calls this. */
  onRemove?: (e: React.SyntheticEvent) => void;
  /** Lucide icon name. */
  icon?: string;
  disabled?: boolean;
}
export declare function Tag(props: TagProps): JSX.Element;
