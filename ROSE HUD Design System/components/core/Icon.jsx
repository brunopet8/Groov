import React, { useEffect, useState } from 'react';

const CDN = 'https://unpkg.com/lucide-static@0.460.0/icons/';
const cache = {};

function load(name) {
  if (!cache[name]) {
    cache[name] = fetch(`${CDN}${name}.svg`)
      .then((r) => (r.ok ? r.text() : ''))
      .then((t) => t.replace(/<!--[\s\S]*?-->/g, '').replace(/<svg[^>]*>/, (tag) => tag.replace(/\s(width|height|class)="[^"]*"/g, '')))
      .catch(() => '');
  }
  return cache[name];
}

export function Icon({ name, size = 12, color = 'currentColor', strokeWidth = 2, style, ...rest }) {
  const [svg, setSvg] = useState('');
  useEffect(() => {
    let live = true;
    load(name).then((t) => { if (live) setSvg(t); });
    return () => { live = false; };
  }, [name]);
  const html = svg.replace('<svg', `<svg width="100%" height="100%" style="display:block"`).replace(/stroke-width="[^"]*"/, `stroke-width="${strokeWidth}"`);
  return (
    <span
      aria-hidden="true"
      {...rest}
      dangerouslySetInnerHTML={{ __html: html }}
      style={{ display: 'inline-block', flex: 'none', width: size, height: size, color, lineHeight: 0, transition: 'color var(--dur-base) var(--ease-out)', ...style }}
    />
  );
}
