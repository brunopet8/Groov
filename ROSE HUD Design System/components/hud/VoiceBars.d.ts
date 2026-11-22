import * as React from 'react';

/** Animated voice-level bars for the transcript strip; flatten to gray when inactive. */
export interface VoiceBarsProps {
  /** @default 24 */
  count?: number;
  /** Animate (speaking/listening). @default true */
  active?: boolean;
  /** @default 18 */
  height?: number;
  /** @default 2 */
  barWidth?: number;
  /** @default 2 */
  gap?: number;
  /** @default "red" */
  tone?: 'red' | 'rose' | 'white';
  style?: React.CSSProperties;
}
export declare function VoiceBars(props: VoiceBarsProps): JSX.Element;
