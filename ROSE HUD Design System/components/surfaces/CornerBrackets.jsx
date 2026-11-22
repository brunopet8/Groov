import React from 'react';

export function CornerBrackets({
  color = 'var(--fg-3)', activeColor = 'var(--red-400)', active = false,
  size = 8, activeSize, weight = 1, offset = -1, glow = true,
}) {
  const s = active ? (activeSize ?? size + 6) : size;
  const c = active ? activeColor : color;
  const base = {
    position: 'absolute', width: s, height: s, borderStyle: 'solid', borderColor: c, borderWidth: 0,
    pointerEvents: 'none', zIndex: 2,
    transition: 'width var(--dur-base) var(--ease-out), height var(--dur-base) var(--ease-out), border-color var(--dur-base) var(--ease-out), filter var(--dur-slow) var(--ease-out)',
    filter: active && glow ? 'drop-shadow(0 0 3px var(--red-500))' : 'none',
  };
  return (
    <>
      <span style={{ ...base, top: offset, left: offset, borderTopWidth: weight, borderLeftWidth: weight }} />
      <span style={{ ...base, top: offset, right: offset, borderTopWidth: weight, borderRightWidth: weight }} />
      <span style={{ ...base, bottom: offset, left: offset, borderBottomWidth: weight, borderLeftWidth: weight }} />
      <span style={{ ...base, bottom: offset, right: offset, borderBottomWidth: weight, borderRightWidth: weight }} />
    </>
  );
}
