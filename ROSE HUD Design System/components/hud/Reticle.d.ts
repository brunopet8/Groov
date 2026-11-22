import * as React from 'react';

/**
 * The GROOV orb / core: tick dial, counter-rotating hairline rings with an orbiting satellite, a breathing red arc pair,
 * pulsing core glow. `view="3d"` tilts the stack in perspective, separates layers in depth, adds two gyroscope rings
 * spinning on X/Y, wobbles continuously and tilts toward the pointer. Children render flat and centered.
 */
export interface ReticleProps {
  /** Pixel diameter. @default 180 */
  size?: number;
  /** off = gray/still · idle/online = steady · listening = faster + sonar pings · thinking = fastest. @default "idle" */
  state?: 'off' | 'idle' | 'online' | 'listening' | 'thinking';
  /** red (default) or hot rose. */
  tone?: 'red' | 'rose';
  /** Flat dial or 3D gyroscope. Switching animates the tilt over 1.2s. @default "2d" */
  view?: '2d' | '3d';
  /** 3D tilt on X in degrees. @default 52 */
  tilt?: number;
  /** 3D only: stack tilts toward the pointer. @default true */
  interactive?: boolean;
  /** 72-tick outer dial. @default true */
  ticks?: boolean;
  /** Tiny mono text orbiting the ring, e.g. "GROOV // CORE 01". */
  ringText?: string;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function Reticle(props: ReticleProps): JSX.Element;
