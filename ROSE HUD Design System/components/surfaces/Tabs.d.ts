import * as React from 'react';

/** Tracked-caps tabs. `line`: a glowing red underline glides between tabs. `chips`: bordered chip row. */
export interface TabItem { id: string; label: React.ReactNode; count?: number; }
export interface TabsProps {
  items: Array<string | TabItem>;
  /** Selected tab id. */
  value: string;
  onChange?: (id: string) => void;
  /** @default "line" */
  variant?: 'line' | 'chips';
  style?: React.CSSProperties;
}
export declare function Tabs(props: TabsProps): JSX.Element;
