/** Four L-shaped corner ticks — the signature HUD frame. Place inside a `position: relative` box. */
export interface CornerBracketsProps {
  /** Resting tick color. @default "var(--fg-3)" */
  color?: string;
  /** Tick color when active. @default "var(--red-400)" */
  activeColor?: string;
  /** Ignite: ticks grow, turn red, glow. Drive from hover/focus/selected. */
  active?: boolean;
  /** Tick arm length in px. @default 8 */
  size?: number;
  /** Arm length when active. @default size + 6 */
  activeSize?: number;
  /** Stroke width. @default 1 */
  weight?: number;
  /** Offset from the box edge (−1 sits on a 1px border). @default -1 */
  offset?: number;
  /** Red drop-shadow when active. @default true */
  glow?: boolean;
}
export declare function CornerBrackets(props: CornerBracketsProps): JSX.Element;
