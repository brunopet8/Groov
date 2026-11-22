import * as React from 'react';

/** Lucide glyph (CDN substitute), fetched once per name and inlined as SVG so it inherits currentColor. */
export interface IconProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Lucide icon name, kebab-case, e.g. "x", "mic", "chevron-down". */
  name: string;
  /** Pixel size. 12 in controls, 14 in toolbars. @default 12 */
  size?: number;
  /** Any CSS color. @default "currentColor" */
  color?: string;
  /** SVG stroke width (24-unit grid). @default 2 */
  strokeWidth?: number;
}
export declare function Icon(props: IconProps): JSX.Element;
