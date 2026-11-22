import * as React from 'react';

/** Glowing status dot with optional tracked-caps label ("— ONLINE —"). Hot tones pulse; `live` also pings. */
export interface StatusDotProps {
  /** Palette-only status. Or pass any CSS color. @default "online" */
  tone?: 'online' | 'live' | 'idle' | 'ok' | 'warn' | 'error' | string;
  label?: React.ReactNode;
  /** Dot diameter. @default 6 */
  size?: number;
  /** @default true for online/live/error */
  pulse?: boolean;
  /** Sonar ring. @default true for live */
  ping?: boolean;
  /** Dash-bracket the label: — ONLINE —. */
  bracketed?: boolean;
  style?: React.CSSProperties;
}
export declare function StatusDot(props: StatusDotProps): JSX.Element;
