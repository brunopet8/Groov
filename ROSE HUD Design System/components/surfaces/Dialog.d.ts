import * as React from 'react';

/** Modal: blurred black scrim + a lit Panel that scales in. Esc / scrim click closes. */
export interface DialogProps {
  open: boolean;
  onClose?: () => void;
  /** Header micro text. */
  eyebrow?: React.ReactNode;
  /** Mono caps title. */
  title?: React.ReactNode;
  children?: React.ReactNode;
  /** Buttons, right-aligned in the footer strip. */
  actions?: React.ReactNode;
  /** @default 360 */
  width?: number | string;
}
export declare function Dialog(props: DialogProps): JSX.Element | null;
