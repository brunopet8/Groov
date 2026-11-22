import * as React from 'react';

/**
 * The floating HUD panel — the system's card. Translucent ink, hairline border, corner brackets,
 * 22px header strip; on hover the border and brackets ignite red and a light follows the cursor.
 */
export interface PanelProps extends Omit<React.HTMLAttributes<HTMLElement>, 'title'> {
  /** Micro caps text in the header strip (source, section). */
  eyebrow?: React.ReactNode;
  /** Right-aligned micro text in the header (ID, version). Turns red on hover. */
  meta?: React.ReactNode;
  /** Mono bold caps title at the top of the body. */
  title?: React.ReactNode;
  children?: React.ReactNode;
  /** Footer strip content. */
  footer?: React.ReactNode;
  /** Shows a × in the header. */
  onClose?: () => void;
  /** Extra header controls before the ×. */
  actions?: React.ReactNode;
  /** Permanently lit (selected / speaking-about). */
  active?: boolean;
  /** @default true */
  brackets?: boolean;
  /** Cursor-following light + hover ignite. @default true */
  interactive?: boolean;
  /** Scale-in on mount. @default true */
  enter?: boolean;
  /** Enter delay in ms, for staggering. @default 0 */
  delay?: number;
  padding?: number | string;
  width?: number | string;
  height?: number | string;
  bodyStyle?: React.CSSProperties;
}
export declare function Panel(props: PanelProps): JSX.Element;
