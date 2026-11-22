/* @ds-bundle: {"format":4,"namespace":"ROSEHUDDesignSystem_bed3b4","components":[{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Icon","sourcePath":"components/core/Icon.jsx"},{"name":"IconButton","sourcePath":"components/core/IconButton.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"Tooltip","sourcePath":"components/core/Tooltip.jsx"},{"name":"Progress","sourcePath":"components/feedback/Progress.jsx"},{"name":"StatusDot","sourcePath":"components/feedback/StatusDot.jsx"},{"name":"Toast","sourcePath":"components/feedback/Toast.jsx"},{"name":"Checkbox","sourcePath":"components/forms/Checkbox.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Radio","sourcePath":"components/forms/Radio.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Switch","sourcePath":"components/forms/Switch.jsx"},{"name":"BarChart","sourcePath":"components/hud/BarChart.jsx"},{"name":"Reticle","sourcePath":"components/hud/Reticle.jsx"},{"name":"Stat","sourcePath":"components/hud/Stat.jsx"},{"name":"VoiceBars","sourcePath":"components/hud/VoiceBars.jsx"},{"name":"CornerBrackets","sourcePath":"components/surfaces/CornerBrackets.jsx"},{"name":"Dialog","sourcePath":"components/surfaces/Dialog.jsx"},{"name":"Panel","sourcePath":"components/surfaces/Panel.jsx"},{"name":"Tabs","sourcePath":"components/surfaces/Tabs.jsx"}],"sourceHashes":{"components/core/Badge.jsx":"6b7525472d6f","components/core/Button.jsx":"79840f2c03db","components/core/Icon.jsx":"354c86095ad7","components/core/IconButton.jsx":"5506fb14f462","components/core/Tag.jsx":"33a7332375de","components/core/Tooltip.jsx":"a306d9d9b204","components/feedback/Progress.jsx":"527170d83a7b","components/feedback/StatusDot.jsx":"e3334d35fe00","components/feedback/Toast.jsx":"bef58f09e557","components/forms/Checkbox.jsx":"6adab4059714","components/forms/Input.jsx":"6d0cabf1838d","components/forms/Radio.jsx":"3d9b069e28b0","components/forms/Select.jsx":"04b2a9058f52","components/forms/Switch.jsx":"a5296e928994","components/hud/BarChart.jsx":"e40e2bb8ca56","components/hud/Reticle.jsx":"fa63f4d09468","components/hud/Stat.jsx":"b1e9c135a5a3","components/hud/VoiceBars.jsx":"a24624330524","components/surfaces/CornerBrackets.jsx":"5bbd0bde5b31","components/surfaces/Dialog.jsx":"b793cb9c1c1e","components/surfaces/Panel.jsx":"c34efa35c5fd","components/surfaces/Tabs.jsx":"ff55c37b0ece","ui_kits/groov-hud/App.jsx":"56ce49addbc6","ui_kits/groov-hud/BootScreen.jsx":"777f6361a13b","ui_kits/groov-hud/CoreRings.jsx":"e7cb93c55d00","ui_kits/groov-hud/Dashboard.jsx":"d45ccf392e92","ui_kits/groov-hud/HudChrome.jsx":"3c155f75532b","ui_kits/groov-hud/TranscriptColumn.jsx":"93032dfde557"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.ROSEHUDDesignSystem_bed3b4 = window.ROSEHUDDesignSystem_bed3b4 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Badge({
  children,
  tone = 'neutral',
  variant = 'soft',
  dot = false,
  style,
  ...rest
}) {
  const c = {
    neutral: 'var(--fg-2)',
    red: 'var(--red-400)',
    rose: 'var(--rose-200)',
    white: 'var(--fg-1)'
  }[tone] || 'var(--fg-2)';
  const bg = {
    neutral: 'var(--white-a08)',
    red: 'var(--red-a14)',
    rose: 'var(--rose-a08)',
    white: 'var(--white-a12)'
  }[tone];
  const solid = variant === 'solid';
  return /*#__PURE__*/React.createElement("span", _extends({}, rest, {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      height: 16,
      padding: '0 5px',
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wide)',
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
      borderRadius: 'var(--radius-sm)',
      color: solid ? tone === 'red' ? 'var(--fg-on-accent)' : 'var(--ink-50)' : c,
      background: solid ? tone === 'red' ? 'var(--accent)' : c : variant === 'outline' ? 'transparent' : bg,
      border: variant === 'outline' ? `1px solid ${c}` : '1px solid transparent',
      boxShadow: solid && tone === 'red' ? 'var(--glow-red-xs)' : 'none',
      ...style
    }
  }), dot && /*#__PURE__*/React.createElement("span", {
    style: {
      width: 4,
      height: 4,
      borderRadius: '50%',
      background: 'currentColor',
      boxShadow: '0 0 4px currentColor'
    }
  }), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Icon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  useEffect,
  useState
} = React;
const CDN = 'https://unpkg.com/lucide-static@0.460.0/icons/';
const cache = {};
function load(name) {
  if (!cache[name]) {
    cache[name] = fetch(`${CDN}${name}.svg`).then(r => r.ok ? r.text() : '').then(t => t.replace(/<!--[\s\S]*?-->/g, '').replace(/<svg[^>]*>/, tag => tag.replace(/\s(width|height|class)="[^"]*"/g, ''))).catch(() => '');
  }
  return cache[name];
}
function Icon({
  name,
  size = 12,
  color = 'currentColor',
  strokeWidth = 2,
  style,
  ...rest
}) {
  const [svg, setSvg] = useState('');
  useEffect(() => {
    let live = true;
    load(name).then(t => {
      if (live) setSvg(t);
    });
    return () => {
      live = false;
    };
  }, [name]);
  const html = svg.replace('<svg', `<svg width="100%" height="100%" style="display:block"`).replace(/stroke-width="[^"]*"/, `stroke-width="${strokeWidth}"`);
  return /*#__PURE__*/React.createElement("span", _extends({
    "aria-hidden": "true"
  }, rest, {
    dangerouslySetInnerHTML: {
      __html: html
    },
    style: {
      display: 'inline-block',
      flex: 'none',
      width: size,
      height: size,
      color,
      lineHeight: 0,
      transition: 'color var(--dur-base) var(--ease-out)',
      ...style
    }
  }));
}
Object.assign(__ds_scope, { Icon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Icon.jsx", error: String((e && e.message) || e) }); }

// components/core/IconButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  useState
} = React;
const DIM = {
  sm: 22,
  md: 28,
  lg: 34
};
const ICON = {
  sm: 11,
  md: 13,
  lg: 15
};
function IconButton({
  icon,
  label,
  size = 'md',
  variant = 'ghost',
  active = false,
  disabled = false,
  onClick,
  style,
  ...rest
}) {
  const [hover, setHover] = useState(false);
  const h = hover && !disabled;
  const d = DIM[size] || DIM.md;
  const on = active;
  const look = {
    ghost: {
      background: on ? 'var(--red-a14)' : h ? 'var(--white-a04)' : 'transparent',
      border: `1px solid ${on ? 'var(--red-a40)' : 'transparent'}`
    },
    outline: {
      background: on ? 'var(--red-a14)' : 'transparent',
      border: `1px solid ${on ? 'var(--red-500)' : h ? 'var(--border-strong)' : 'var(--border-default)'}`
    },
    solid: {
      background: h ? 'var(--accent-hover)' : 'var(--accent)',
      border: '1px solid transparent',
      boxShadow: h ? 'var(--glow-red-md)' : 'var(--glow-red-xs)'
    }
  }[variant];
  const color = variant === 'solid' ? 'var(--fg-on-accent)' : on ? 'var(--red-400)' : h ? 'var(--fg-1)' : 'var(--fg-2)';
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    "aria-label": label,
    title: label,
    "aria-pressed": active || undefined,
    disabled: disabled,
    onClick: onClick,
    onPointerEnter: () => setHover(true),
    onPointerLeave: () => setHover(false)
  }, rest, {
    style: {
      display: 'inline-grid',
      placeItems: 'center',
      width: d,
      height: d,
      padding: 0,
      color,
      borderRadius: 'var(--radius-sm)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.35 : 1,
      filter: on && variant !== 'solid' ? 'drop-shadow(0 0 4px rgba(240,31,51,.6))' : 'none',
      transition: 'var(--transition-color), filter var(--dur-slow) var(--ease-out)',
      ...look,
      ...style
    }
  }), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: ICON[size] || 13
  }));
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  useState
} = React;
function Tag({
  children,
  selected = false,
  onClick,
  onRemove,
  icon,
  disabled = false,
  style,
  ...rest
}) {
  const [hover, setHover] = useState(false);
  const h = hover && !disabled;
  const interactive = !!onClick;
  return /*#__PURE__*/React.createElement("span", _extends({
    role: interactive ? 'button' : undefined,
    tabIndex: interactive && !disabled ? 0 : undefined,
    "aria-pressed": interactive ? selected : undefined,
    onClick: disabled ? undefined : onClick,
    onKeyDown: e => {
      if (interactive && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        onClick(e);
      }
    },
    onPointerEnter: () => setHover(true),
    onPointerLeave: () => setHover(false)
  }, rest, {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      height: 20,
      padding: '0 7px',
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wider)',
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
      borderRadius: 'var(--radius-sm)',
      userSelect: 'none',
      cursor: disabled ? 'not-allowed' : interactive ? 'pointer' : 'default',
      opacity: disabled ? 0.35 : 1,
      color: selected ? 'var(--fg-1)' : h && interactive ? 'var(--fg-1)' : 'var(--fg-2)',
      background: selected ? 'var(--red-a14)' : 'var(--surface-panel)',
      border: `1px solid ${selected ? 'var(--red-500)' : h && interactive ? 'var(--border-strong)' : 'var(--border-default)'}`,
      boxShadow: selected ? 'var(--glow-red-xs)' : 'none',
      transition: 'var(--transition-color)',
      ...style
    }
  }), icon && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 10
  }), children, onRemove && /*#__PURE__*/React.createElement("span", {
    role: "button",
    "aria-label": "Remove",
    onClick: e => {
      e.stopPropagation();
      onRemove(e);
    },
    style: {
      display: 'inline-grid',
      placeItems: 'center',
      marginRight: -3,
      cursor: 'pointer',
      color: 'var(--fg-3)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "x",
    size: 9
  })));
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/core/Tooltip.jsx
try { (() => {
const {
  useState
} = React;
const POS = {
  top: {
    bottom: '100%',
    left: '50%',
    transform: 'translate(-50%,-6px)'
  },
  bottom: {
    top: '100%',
    left: '50%',
    transform: 'translate(-50%,6px)'
  },
  left: {
    right: '100%',
    top: '50%',
    transform: 'translate(-6px,-50%)'
  },
  right: {
    left: '100%',
    top: '50%',
    transform: 'translate(6px,-50%)'
  }
};
function Tooltip({
  content,
  placement = 'top',
  children,
  delay = 120,
  style
}) {
  const [open, setOpen] = useState(false);
  const [t, setT] = useState(null);
  const show = () => setT(setTimeout(() => setOpen(true), delay));
  const hide = () => {
    clearTimeout(t);
    setOpen(false);
  };
  return /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'relative',
      display: 'inline-flex',
      ...style
    },
    onPointerEnter: show,
    onPointerLeave: hide,
    onFocus: show,
    onBlur: hide
  }, children, open && /*#__PURE__*/React.createElement("span", {
    role: "tooltip",
    style: {
      position: 'absolute',
      zIndex: 50,
      pointerEvents: 'none',
      whiteSpace: 'nowrap',
      ...POS[placement],
      padding: '4px 7px',
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wide)',
      textTransform: 'uppercase',
      color: 'var(--fg-1)',
      background: 'var(--ink-150)',
      border: '1px solid var(--red-a40)',
      boxShadow: 'var(--glow-red-xs)',
      animation: 'groov-fade-in var(--dur-fast) var(--ease-out)'
    }
  }, content));
}
Object.assign(__ds_scope, { Tooltip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tooltip.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Progress.jsx
try { (() => {
function Progress({
  value = 0,
  label,
  showValue = true,
  size = 'md',
  tone = 'red',
  indeterminate = false,
  width = '100%',
  style
}) {
  const v = Math.max(0, Math.min(100, value));
  const h = size === 'sm' ? 2 : size === 'lg' ? 8 : 6;
  const fill = tone === 'rose' ? 'var(--grad-rose-red)' : tone === 'white' ? 'var(--fg-1)' : 'var(--grad-red-bar)';
  const glow = tone === 'white' ? 'var(--glow-white-sm)' : tone === 'rose' ? 'var(--glow-rose-sm)' : 'var(--glow-red-sm)';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      width,
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("div", {
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--tracking-widest)',
      textTransform: 'uppercase',
      color: 'var(--fg-1)',
      textAlign: 'center'
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    role: "progressbar",
    "aria-valuenow": indeterminate ? undefined : v,
    "aria-valuemin": 0,
    "aria-valuemax": 100,
    style: {
      position: 'relative',
      flex: 1,
      height: h,
      overflow: 'hidden',
      borderRadius: 'var(--radius-pill)',
      background: 'var(--ink-200)',
      border: size === 'sm' ? 0 : '1px solid var(--border-subtle)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 0,
      bottom: 0,
      left: 0,
      borderRadius: 'inherit',
      background: fill,
      boxShadow: glow,
      width: indeterminate ? '35%' : `${v}%`,
      animation: indeterminate ? 'groov-sweep 1.4s var(--ease-in-out) infinite' : 'none',
      transition: 'width var(--dur-slower) var(--ease-out)'
    }
  }, !indeterminate && v > 0 && /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      inset: 0,
      overflow: 'hidden',
      borderRadius: 'inherit'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      top: 0,
      bottom: 0,
      width: '40%',
      background: 'var(--grad-red-sweep)',
      opacity: 0.6,
      animation: 'groov-sweep 2.2s var(--ease-in-out) infinite'
    }
  })))), showValue && !indeterminate && /*#__PURE__*/React.createElement("span", {
    style: {
      minWidth: 30,
      textAlign: 'right',
      font: 'var(--type-data)',
      fontSize: 'var(--fs-xs)',
      letterSpacing: 'var(--tracking-wide)',
      color: 'var(--fg-1)',
      fontVariantNumeric: 'tabular-nums'
    }
  }, Math.round(v), "%")));
}
Object.assign(__ds_scope, { Progress });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Progress.jsx", error: String((e && e.message) || e) }); }

// components/feedback/StatusDot.jsx
try { (() => {
const TONE = {
  online: 'var(--status-online)',
  live: 'var(--status-live)',
  idle: 'var(--status-idle)',
  ok: 'var(--status-ok)',
  warn: 'var(--status-warn)',
  error: 'var(--status-error)'
};
function StatusDot({
  tone = 'online',
  label,
  size = 6,
  pulse,
  ping,
  bracketed = false,
  style
}) {
  const c = TONE[tone] || tone;
  const hot = tone === 'online' || tone === 'live' || tone === 'error';
  const doPulse = pulse ?? hot;
  const doPing = ping ?? tone === 'live';
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      color: c,
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'relative',
      display: 'inline-grid',
      placeItems: 'center',
      width: size,
      height: size,
      flex: 'none'
    }
  }, doPing && /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      inset: -size,
      borderRadius: '50%',
      border: `1px solid ${c}`,
      animation: 'groov-ping 1.8s var(--ease-out) infinite'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      width: size,
      height: size,
      borderRadius: '50%',
      background: c,
      boxShadow: hot ? `0 0 ${size + 2}px ${c}` : 'none',
      animation: doPulse ? 'groov-pulse var(--dur-pulse) var(--ease-in-out) infinite' : 'none'
    }
  })), label && /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      font: 'var(--type-label)',
      letterSpacing: 'var(--tracking-widest)',
      textTransform: 'uppercase',
      textShadow: hot ? 'var(--text-glow-red)' : 'none'
    }
  }, bracketed && /*#__PURE__*/React.createElement("span", {
    style: {
      width: 8,
      height: 1,
      background: 'currentColor'
    }
  }), label, bracketed && /*#__PURE__*/React.createElement("span", {
    style: {
      width: 8,
      height: 1,
      background: 'currentColor'
    }
  })));
}
Object.assign(__ds_scope, { StatusDot });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/StatusDot.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Toast.jsx
try { (() => {
const {
  useEffect,
  useState
} = React;
function Toast({
  title,
  message,
  tone = 'neutral',
  icon,
  duration = 0,
  onClose,
  action,
  style
}) {
  const [left, setLeft] = useState(100);
  useEffect(() => {
    if (!duration) return;
    const id = setTimeout(() => setLeft(0), 30);
    const t = setTimeout(() => onClose && onClose(), duration);
    return () => {
      clearTimeout(id);
      clearTimeout(t);
    };
  }, [duration]);
  const c = tone === 'red' ? 'var(--red-400)' : tone === 'rose' ? 'var(--rose-200)' : 'var(--fg-1)';
  const border = tone === 'red' ? 'var(--red-a40)' : tone === 'rose' ? 'var(--rose-a32)' : 'var(--border-default)';
  return /*#__PURE__*/React.createElement("div", {
    role: "status",
    style: {
      position: 'relative',
      display: 'flex',
      alignItems: 'flex-start',
      gap: 10,
      width: 280,
      padding: '10px 8px 10px 10px',
      overflow: 'hidden',
      background: 'var(--surface-panel)',
      backdropFilter: 'blur(var(--blur-panel))',
      border: `1px solid ${border}`,
      boxShadow: tone === 'red' ? 'var(--glow-inset-red)' : 'none',
      animation: 'groov-fade-up var(--dur-slow) var(--ease-out)',
      ...style
    }
  }, icon && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 13,
    color: c,
    style: {
      marginTop: 1,
      filter: tone === 'red' ? 'drop-shadow(0 0 4px var(--red-500))' : 'none'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0,
      display: 'flex',
      flexDirection: 'column',
      gap: 3
    }
  }, title && /*#__PURE__*/React.createElement("div", {
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--tracking-wider)',
      textTransform: 'uppercase',
      color: c
    }
  }, title), message && /*#__PURE__*/React.createElement("div", {
    style: {
      font: 'var(--type-body-sm)',
      color: 'var(--fg-2)'
    }
  }, message), action && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 4
    }
  }, action)), onClose && /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    label: "Dismiss",
    size: "sm",
    onClick: onClose,
    style: {
      width: 18,
      height: 18,
      marginTop: -2
    }
  }), duration > 0 && /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      left: 0,
      bottom: 0,
      height: 1,
      width: `${left}%`,
      background: c,
      boxShadow: `0 0 6px ${c}`,
      transition: `width ${duration}ms linear`
    }
  }));
}
Object.assign(__ds_scope, { Toast });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Toast.jsx", error: String((e && e.message) || e) }); }

// components/forms/Checkbox.jsx
try { (() => {
const {
  useState
} = React;
function Checkbox({
  checked,
  defaultChecked = false,
  onChange,
  label,
  disabled = false,
  style
}) {
  const [inner, setInner] = useState(defaultChecked);
  const [hover, setHover] = useState(false);
  const on = checked ?? inner;
  const toggle = () => {
    if (disabled) return;
    if (checked === undefined) setInner(!on);
    onChange && onChange(!on);
  };
  return /*#__PURE__*/React.createElement("label", {
    onPointerEnter: () => setHover(true),
    onPointerLeave: () => setHover(false),
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.4 : 1,
      userSelect: 'none',
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    role: "checkbox",
    "aria-checked": on,
    tabIndex: disabled ? -1 : 0,
    onClick: toggle,
    onKeyDown: e => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        toggle();
      }
    },
    style: {
      display: 'grid',
      placeItems: 'center',
      width: 12,
      height: 12,
      flex: 'none',
      borderRadius: 'var(--radius-xs)',
      background: on ? 'var(--accent)' : 'transparent',
      color: 'var(--fg-on-accent)',
      border: `1px solid ${on ? 'var(--accent)' : hover ? 'var(--red-400)' : 'var(--border-strong)'}`,
      boxShadow: on ? 'var(--glow-red-sm)' : 'none',
      transition: 'var(--transition-color)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "check",
    size: 9,
    style: {
      opacity: on ? 1 : 0,
      transform: on ? 'scale(1)' : 'scale(.4)',
      transition: 'all var(--dur-base) var(--ease-spring)'
    }
  })), label && /*#__PURE__*/React.createElement("span", {
    onClick: toggle,
    style: {
      font: 'var(--type-body-sm)',
      color: on || hover ? 'var(--fg-1)' : 'var(--fg-2)',
      transition: 'var(--transition-color)'
    }
  }, label));
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/forms/Radio.jsx
try { (() => {
const {
  useState
} = React;
function Radio({
  options = [],
  value,
  defaultValue,
  onChange,
  name,
  direction = 'column',
  disabled = false,
  style
}) {
  const [inner, setInner] = useState(defaultValue);
  const [hov, setHov] = useState(null);
  const cur = value ?? inner;
  const opts = options.map(o => typeof o === 'string' ? {
    value: o,
    label: o
  } : o);
  const pick = v => {
    if (disabled) return;
    if (value === undefined) setInner(v);
    onChange && onChange(v);
  };
  return /*#__PURE__*/React.createElement("div", {
    role: "radiogroup",
    "aria-label": name,
    style: {
      display: 'flex',
      flexDirection: direction,
      gap: direction === 'row' ? 16 : 8,
      opacity: disabled ? 0.4 : 1,
      ...style
    }
  }, opts.map(o => {
    const on = o.value === cur;
    const h = hov === o.value;
    return /*#__PURE__*/React.createElement("label", {
      key: o.value,
      onPointerEnter: () => setHov(o.value),
      onPointerLeave: () => setHov(null),
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        cursor: disabled ? 'not-allowed' : 'pointer',
        userSelect: 'none'
      }
    }, /*#__PURE__*/React.createElement("span", {
      role: "radio",
      "aria-checked": on,
      tabIndex: disabled ? -1 : 0,
      onClick: () => pick(o.value),
      onKeyDown: e => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          pick(o.value);
        }
      },
      style: {
        display: 'grid',
        placeItems: 'center',
        width: 12,
        height: 12,
        flex: 'none',
        borderRadius: '50%',
        border: `1px solid ${on ? 'var(--red-500)' : h ? 'var(--red-400)' : 'var(--border-strong)'}`,
        boxShadow: on ? 'var(--glow-red-xs)' : 'none',
        transition: 'var(--transition-color)'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: 'var(--red-400)',
        boxShadow: 'var(--glow-red-sm)',
        transform: on ? 'scale(1)' : 'scale(0)',
        transition: 'transform var(--dur-base) var(--ease-spring)'
      }
    })), /*#__PURE__*/React.createElement("span", {
      onClick: () => pick(o.value),
      style: {
        font: 'var(--type-body-sm)',
        color: on || h ? 'var(--fg-1)' : 'var(--fg-2)',
        transition: 'var(--transition-color)'
      }
    }, o.label));
  }));
}
Object.assign(__ds_scope, { Radio });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Radio.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
const {
  useEffect,
  useRef,
  useState
} = React;
function Select({
  options = [],
  value,
  onChange,
  placeholder = 'Select',
  label,
  size = 'md',
  disabled = false,
  width,
  style
}) {
  const [open, setOpen] = useState(false);
  const [hover, setHover] = useState(false);
  const [hi, setHi] = useState(-1);
  const ref = useRef(null);
  const opts = options.map(o => typeof o === 'string' ? {
    value: o,
    label: o
  } : o);
  const cur = opts.find(o => o.value === value);
  const h = size === 'sm' ? 'var(--control-h-sm)' : size === 'lg' ? 'var(--control-h-lg)' : 'var(--control-h-md)';
  useEffect(() => {
    if (!open) return;
    const off = e => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('pointerdown', off);
    return () => document.removeEventListener('pointerdown', off);
  }, [open]);
  const pick = o => {
    onChange && onChange(o.value);
    setOpen(false);
  };
  const onKey = e => {
    if (e.key === 'Escape') setOpen(false);else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setHi(i => Math.min(opts.length - 1, i + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHi(i => Math.max(0, i - 1));
    } else if (e.key === 'Enter' && open && hi >= 0) {
      e.preventDefault();
      pick(opts[hi]);
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    ref: ref,
    style: {
      position: 'relative',
      display: 'inline-flex',
      flexDirection: 'column',
      gap: 5,
      width,
      opacity: disabled ? 0.4 : 1,
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wider)',
      textTransform: 'uppercase',
      color: 'var(--fg-3)'
    }
  }, label), /*#__PURE__*/React.createElement("button", {
    type: "button",
    disabled: disabled,
    "aria-haspopup": "listbox",
    "aria-expanded": open,
    onClick: () => setOpen(o => !o),
    onKeyDown: onKey,
    onPointerEnter: () => setHover(true),
    onPointerLeave: () => setHover(false),
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 10,
      height: h,
      padding: '0 8px',
      minWidth: 120,
      background: 'var(--surface-sunken)',
      color: cur ? 'var(--fg-1)' : 'var(--fg-3)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      border: `1px solid ${open ? 'var(--red-500)' : hover ? 'var(--border-strong)' : 'var(--border-default)'}`,
      borderRadius: 'var(--radius-xs)',
      boxShadow: open ? 'var(--glow-red-xs)' : 'none',
      font: 'var(--type-micro)',
      fontSize: size === 'lg' ? 'var(--fs-xs)' : 'var(--fs-2xs)',
      letterSpacing: 'var(--tracking-wide)',
      textTransform: 'uppercase',
      transition: 'var(--transition-color)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, cur ? cur.label : placeholder), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-down",
    size: 11,
    color: open ? 'var(--red-400)' : 'var(--fg-3)',
    style: {
      transform: open ? 'rotate(180deg)' : 'none',
      transition: 'transform var(--dur-base) var(--ease-out)'
    }
  })), open && /*#__PURE__*/React.createElement("div", {
    role: "listbox",
    style: {
      position: 'absolute',
      top: '100%',
      left: 0,
      right: 0,
      marginTop: 4,
      zIndex: 40,
      padding: 3,
      background: 'var(--ink-100)',
      border: '1px solid var(--border-default)',
      backdropFilter: 'blur(var(--blur-panel))',
      boxShadow: '0 12px 32px rgba(0,0,0,.6)',
      animation: 'groov-fade-up var(--dur-base) var(--ease-out)'
    }
  }, opts.map((o, i) => {
    const sel = o.value === value;
    const act = i === hi;
    return /*#__PURE__*/React.createElement("div", {
      key: o.value,
      role: "option",
      "aria-selected": sel,
      onPointerEnter: () => setHi(i),
      onClick: () => pick(o),
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 8,
        padding: '6px 7px',
        cursor: 'pointer',
        font: 'var(--type-micro)',
        fontSize: 'var(--fs-2xs)',
        letterSpacing: 'var(--tracking-wide)',
        textTransform: 'uppercase',
        color: sel || act ? 'var(--fg-1)' : 'var(--fg-2)',
        background: act ? 'var(--red-a14)' : 'transparent',
        transition: 'background-color var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out)'
      }
    }, o.label, sel && /*#__PURE__*/React.createElement("span", {
      style: {
        width: 5,
        height: 5,
        borderRadius: '50%',
        background: 'var(--red-500)',
        boxShadow: 'var(--glow-red-sm)'
      }
    }));
  })));
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Switch.jsx
try { (() => {
const {
  useState
} = React;
function Switch({
  checked,
  defaultChecked = false,
  onChange,
  label,
  disabled = false,
  style
}) {
  const [inner, setInner] = useState(defaultChecked);
  const [hover, setHover] = useState(false);
  const on = checked ?? inner;
  const toggle = () => {
    if (disabled) return;
    if (checked === undefined) setInner(!on);
    onChange && onChange(!on);
  };
  return /*#__PURE__*/React.createElement("label", {
    onPointerEnter: () => setHover(true),
    onPointerLeave: () => setHover(false),
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.4 : 1,
      userSelect: 'none',
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    role: "switch",
    "aria-checked": on,
    tabIndex: disabled ? -1 : 0,
    onClick: toggle,
    onKeyDown: e => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        toggle();
      }
    },
    style: {
      position: 'relative',
      width: 26,
      height: 14,
      flex: 'none',
      borderRadius: 'var(--radius-pill)',
      background: on ? 'var(--red-a40)' : 'var(--ink-300)',
      border: `1px solid ${on ? 'var(--red-500)' : hover ? 'var(--border-strong)' : 'var(--border-default)'}`,
      boxShadow: on ? 'var(--glow-red-sm)' : 'none',
      transition: 'var(--transition-color)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      top: 1,
      left: 1,
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: on ? 'var(--white-pure)' : 'var(--fg-2)',
      boxShadow: on ? 'var(--glow-white-sm)' : 'none',
      transform: on ? 'translateX(12px)' : 'none',
      transition: 'transform var(--dur-base) var(--ease-spring), background-color var(--dur-base) var(--ease-out)'
    }
  })), label && /*#__PURE__*/React.createElement("span", {
    onClick: toggle,
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--tracking-wider)',
      textTransform: 'uppercase',
      color: on ? 'var(--fg-1)' : 'var(--fg-2)',
      transition: 'var(--transition-color)'
    }
  }, label));
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Switch.jsx", error: String((e && e.message) || e) }); }

// components/hud/BarChart.jsx
try { (() => {
const {
  useEffect,
  useState
} = React;
function BarChart({
  data = [],
  height = 80,
  highlight = 'max',
  showValues = false,
  unit = '',
  animate = true,
  gap = 6,
  style
}) {
  const [grown, setGrown] = useState(!animate);
  const [hov, setHov] = useState(null);
  useEffect(() => {
    if (animate) {
      const id = setTimeout(() => setGrown(true), 30);
      return () => clearTimeout(id);
    }
  }, []);
  const max = Math.max(1, ...data.map(d => d.value));
  const hiIdx = highlight === 'max' ? data.findIndex(d => d.value === max) : typeof highlight === 'number' ? highlight : -1;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 5,
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-end',
      gap,
      height,
      borderBottom: '1px solid var(--border-strong)'
    }
  }, data.map((d, i) => {
    const red = i === hiIdx || i === hov;
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      onPointerEnter: () => setHov(i),
      onPointerLeave: () => setHov(null),
      style: {
        position: 'relative',
        flex: 1,
        height: '100%',
        display: 'flex',
        alignItems: 'flex-end',
        cursor: 'default'
      }
    }, (showValues || i === hov) && /*#__PURE__*/React.createElement("span", {
      style: {
        position: 'absolute',
        left: '50%',
        transform: 'translateX(-50%)',
        bottom: `calc(${d.value / max * 100}% + 3px)`,
        font: 'var(--type-micro)',
        color: red ? 'var(--red-400)' : 'var(--fg-2)',
        whiteSpace: 'nowrap',
        opacity: grown ? 1 : 0,
        transition: 'opacity var(--dur-slow) var(--ease-out), color var(--dur-fast)'
      }
    }, d.value, unit), /*#__PURE__*/React.createElement("div", {
      style: {
        width: '100%',
        height: grown ? `${d.value / max * 100}%` : '0%',
        background: red ? 'var(--red-500)' : 'rgba(244,244,246,.85)',
        boxShadow: red ? 'var(--glow-red-sm)' : 'none',
        transition: `height var(--dur-slower) var(--ease-out) ${i * 60}ms, background-color var(--dur-base) var(--ease-out), box-shadow var(--dur-base) var(--ease-out)`
      }
    }));
  })), data.some(d => d.label) && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap
    }
  }, data.map((d, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      flex: 1,
      textAlign: 'center',
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wide)',
      textTransform: 'uppercase',
      color: i === hov || i === hiIdx ? 'var(--fg-1)' : 'var(--fg-3)',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
      transition: 'color var(--dur-fast)'
    }
  }, d.label))));
}
Object.assign(__ds_scope, { BarChart });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/hud/BarChart.jsx", error: String((e && e.message) || e) }); }

// components/hud/Reticle.jsx
try { (() => {
const {
  useRef
} = React;
const SPEED = {
  off: 0,
  idle: 1,
  online: 1.15,
  listening: 1.7,
  thinking: 3
};
function Reticle({
  size = 180,
  state = 'idle',
  tone = 'red',
  view = '2d',
  tilt = 52,
  interactive = true,
  ticks = true,
  ringText,
  children,
  style
}) {
  const k = SPEED[state] ?? 1;
  const off = state === 'off';
  const is3d = view === '3d';
  const stageRef = useRef(null);
  const main = off ? 'var(--ink-600)' : tone === 'rose' ? 'var(--rose-500)' : 'var(--red-500)';
  const hot = off ? 'transparent' : tone === 'rose' ? 'rgba(236,63,122,.85)' : 'rgba(255,51,70,.85)';
  const spin = (sec, rev) => k ? `${rev ? 'groov-spin-rev' : 'groov-spin'} ${sec / k}s linear infinite` : 'none';
  const base3d = `rotateX(${tilt}deg) rotateY(-14deg)`;
  const tr = 'transform 1.2s var(--ease-out)';
  const fill = {
    position: 'absolute',
    inset: 0,
    transformStyle: 'preserve-3d'
  };
  const svgS = {
    position: 'absolute',
    inset: 0,
    width: '100%',
    height: '100%',
    overflow: 'visible'
  };
  const layer = (z, extra = '') => ({
    ...fill,
    transform: is3d ? `translateZ(${z * size / 180}px) ${extra}` : 'none',
    transition: tr
  });
  const tickEls = [];
  if (ticks) for (let i = 0; i < 72; i++) {
    const a = i * 5 * Math.PI / 180;
    const long = i % 6 === 0;
    const r1 = long ? 89 : 93,
      r2 = 98;
    tickEls.push(/*#__PURE__*/React.createElement("line", {
      key: i,
      x1: 100 + r1 * Math.sin(a),
      y1: 100 - r1 * Math.cos(a),
      x2: 100 + r2 * Math.sin(a),
      y2: 100 - r2 * Math.cos(a),
      stroke: long ? 'var(--rose-200)' : 'var(--fg-3)',
      strokeOpacity: long ? 0.55 : 0.4,
      strokeWidth: long ? 0.8 : 0.5
    }));
  }
  const onMove = e => {
    if (!is3d || !interactive || !stageRef.current) return;
    const r = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    stageRef.current.style.transform = `rotateX(${tilt - py * 28}deg) rotateY(${-14 + px * 40}deg)`;
  };
  const onLeave = () => {
    if (stageRef.current) stageRef.current.style.transform = is3d ? base3d : 'none';
  };
  return /*#__PURE__*/React.createElement("div", {
    onPointerMove: onMove,
    onPointerLeave: onLeave,
    style: {
      position: 'relative',
      width: size,
      height: size,
      flex: 'none',
      perspective: size * 3.2,
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    "aria-hidden": "true",
    style: {
      position: 'absolute',
      inset: '12%',
      borderRadius: '50%',
      background: off ? 'none' : `radial-gradient(circle, ${tone === 'rose' ? 'rgba(236,63,122,.24)' : 'rgba(240,31,51,.24)'}, transparent 68%)`,
      animation: off ? 'none' : 'groov-pulse var(--dur-pulse) var(--ease-in-out) infinite'
    }
  }), state === 'listening' && [0, 0.7, 1.4].map(d => /*#__PURE__*/React.createElement("span", {
    key: d,
    "aria-hidden": "true",
    style: {
      position: 'absolute',
      inset: '24%',
      borderRadius: '50%',
      border: `1px solid ${main}`,
      animation: `groov-ping 2.1s var(--ease-out) ${d}s infinite`
    }
  })), /*#__PURE__*/React.createElement("div", {
    ref: stageRef,
    style: {
      ...fill,
      transform: is3d ? base3d : 'none',
      transition: tr
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...fill,
      animation: is3d && k ? `groov-wobble ${9 / k}s var(--ease-in-out) infinite` : 'none'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: layer(-18)
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 200 200",
    style: {
      ...svgS,
      animation: spin(40)
    }
  }, tickEls)), /*#__PURE__*/React.createElement("div", {
    style: layer(0, 'rotateY(16deg)')
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 200 200",
    style: {
      ...svgS,
      animation: spin(10, true)
    }
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "100",
    cy: "100",
    r: "84",
    fill: "none",
    stroke: "var(--fg-1)",
    strokeOpacity: ".1",
    strokeWidth: ".6"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "100",
    cy: "100",
    r: "84",
    fill: "none",
    stroke: "var(--fg-1)",
    strokeOpacity: ".45",
    strokeWidth: ".8",
    strokeDasharray: "40 92"
  }), !off && /*#__PURE__*/React.createElement("circle", {
    cx: "100",
    cy: "16",
    r: "2.2",
    fill: "var(--rose-200)",
    style: {
      filter: 'drop-shadow(0 0 3px var(--rose-500))'
    }
  }))), is3d && !off && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    style: {
      ...fill,
      animation: `groov-gyro ${8 / k}s linear infinite`
    }
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 200 200",
    style: svgS
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "100",
    cy: "100",
    r: "80",
    fill: "none",
    stroke: "var(--fg-1)",
    strokeOpacity: ".55",
    strokeWidth: ".9",
    strokeDasharray: "150 40",
    style: {
      filter: 'drop-shadow(0 0 2px rgba(255,255,255,.5))'
    }
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      ...fill,
      transform: 'rotateZ(60deg)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...fill,
      animation: `groov-gyro-x ${11 / k}s linear infinite reverse`
    }
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 200 200",
    style: svgS
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "100",
    cy: "100",
    r: "70",
    fill: "none",
    stroke: tone === 'rose' ? 'var(--rose-200)' : 'var(--rose-300)',
    strokeOpacity: ".5",
    strokeWidth: ".7",
    strokeDasharray: "3 5"
  }))))), /*#__PURE__*/React.createElement("div", {
    style: layer(12)
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 200 200",
    style: {
      ...svgS,
      animation: spin(4.5),
      filter: off ? 'none' : `drop-shadow(0 0 3px ${hot}) drop-shadow(0 0 8px ${hot})`
    }
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "100",
    cy: "100",
    r: "74",
    fill: "none",
    stroke: main,
    strokeWidth: "2.2",
    strokeLinecap: "round",
    strokeDasharray: "130 102.5",
    style: {
      animation: k ? `groov-arc ${3.2 / k}s var(--ease-in-out) infinite` : 'none'
    }
  }), /*#__PURE__*/React.createElement("polygon", {
    points: "100,20 97,15 103,15",
    fill: main
  }))), /*#__PURE__*/React.createElement("div", {
    style: layer(24, 'rotateX(-18deg)')
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 200 200",
    style: {
      ...svgS,
      animation: spin(6, true)
    }
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "100",
    cy: "100",
    r: "64",
    fill: "none",
    stroke: tone === 'rose' ? 'var(--rose-200)' : 'var(--fg-1)',
    strokeOpacity: ".24",
    strokeWidth: ".6",
    strokeDasharray: "2 4"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "100",
    cy: "100",
    r: "58",
    fill: "none",
    stroke: "var(--fg-1)",
    strokeOpacity: ".08",
    strokeWidth: ".6"
  }))), ringText && /*#__PURE__*/React.createElement("div", {
    style: layer(-8)
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 200 200",
    style: {
      ...svgS,
      animation: spin(24)
    }
  }, /*#__PURE__*/React.createElement("defs", null, /*#__PURE__*/React.createElement("path", {
    id: `rt-${size}-${view}`,
    d: "M100,100 m-80,0 a80,80 0 1,1 160,0 a80,80 0 1,1 -160,0"
  })), /*#__PURE__*/React.createElement("text", {
    fill: "var(--rose-200)",
    fillOpacity: ".7",
    style: {
      font: '500 5px var(--font-mono)',
      letterSpacing: '1.4px'
    }
  }, /*#__PURE__*/React.createElement("textPath", {
    href: `#rt-${size}-${view}`,
    startOffset: "62%"
  }, ringText)))))), children != null && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'grid',
      placeItems: 'center',
      textAlign: 'center',
      pointerEvents: 'none'
    }
  }, children));
}
Object.assign(__ds_scope, { Reticle });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/hud/Reticle.jsx", error: String((e && e.message) || e) }); }

// components/hud/Stat.jsx
try { (() => {
const {
  useEffect,
  useRef,
  useState
} = React;
const FS = {
  sm: 'var(--fs-2xl)',
  md: 'var(--fs-3xl)',
  lg: 'var(--fs-4xl)'
};
function Stat({
  value,
  prefix,
  suffix,
  label,
  caption,
  size = 'md',
  tone = 'white',
  decimals = 0,
  animate = true,
  align = 'left',
  style
}) {
  const numeric = typeof value === 'number';
  const [shown, setShown] = useState(numeric && animate ? 0 : value);
  const raf = useRef(0);
  useEffect(() => {
    if (!numeric || !animate) {
      setShown(value);
      return;
    }
    const start = performance.now();
    const from = 0;
    const dur = 1100;
    const tick = t => {
      const p = Math.min(1, (t - start) / dur);
      const e = 1 - Math.pow(1 - p, 4);
      setShown(from + (value - from) * e);
      if (p < 1) raf.current = setTimeout(() => tick(performance.now()), 16);
    };
    raf.current = setTimeout(() => tick(performance.now()), 16);
    return () => clearTimeout(raf.current);
  }, [value]);
  const text = numeric ? Number(shown).toFixed(decimals) : shown;
  const red = tone === 'red';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      alignItems: align === 'center' ? 'center' : 'flex-start',
      textAlign: align,
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("div", {
    style: {
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wider)',
      textTransform: 'uppercase',
      color: 'var(--fg-3)'
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'baseline',
      gap: 2,
      fontFamily: 'var(--font-mono)',
      fontWeight: 300,
      fontSize: FS[size] || FS.md,
      lineHeight: 1,
      letterSpacing: '-0.02em',
      fontVariantNumeric: 'tabular-nums',
      color: red ? 'var(--red-400)' : 'var(--fg-1)',
      textShadow: red ? 'var(--text-glow-red)' : 'var(--text-glow-white)'
    }
  }, prefix && /*#__PURE__*/React.createElement("span", {
    style: {
      opacity: 0.7
    }
  }, prefix), /*#__PURE__*/React.createElement("span", null, text), suffix && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '0.55em',
      color: red ? 'var(--red-300)' : 'var(--fg-2)',
      marginLeft: 2
    }
  }, suffix)), caption && /*#__PURE__*/React.createElement("div", {
    style: {
      font: 'var(--type-body-sm)',
      color: 'var(--fg-2)',
      maxWidth: 240,
      textWrap: 'pretty'
    }
  }, caption));
}
Object.assign(__ds_scope, { Stat });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/hud/Stat.jsx", error: String((e && e.message) || e) }); }

// components/hud/VoiceBars.jsx
try { (() => {
const {
  useMemo
} = React;
function VoiceBars({
  count = 24,
  active = true,
  height = 18,
  barWidth = 2,
  gap = 2,
  tone = 'red',
  style
}) {
  const bars = useMemo(() => Array.from({
    length: count
  }, (_, i) => {
    const s = Math.sin(i * 12.9898) * 43758.5453;
    const r = s - Math.floor(s);
    return {
      d: (r * 0.8).toFixed(2),
      dur: (0.6 + r * 0.7).toFixed(2),
      amp: 0.35 + 0.65 * Math.abs(Math.sin(i / count * Math.PI))
    };
  }), [count]);
  const c = tone === 'rose' ? 'var(--rose-400)' : tone === 'white' ? 'var(--fg-1)' : 'var(--red-500)';
  return /*#__PURE__*/React.createElement("div", {
    "aria-hidden": "true",
    style: {
      display: 'flex',
      alignItems: 'center',
      gap,
      height,
      ...style
    }
  }, bars.map((b, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      width: barWidth,
      height: active ? `${b.amp * 100}%` : 2,
      background: active ? c : 'var(--ink-500)',
      boxShadow: active && tone !== 'white' ? `0 0 4px ${c}` : 'none',
      transformOrigin: 'center',
      borderRadius: 1,
      animation: active ? `groov-bar ${b.dur}s var(--ease-in-out) ${b.d}s infinite` : 'none',
      transition: 'height var(--dur-slow) var(--ease-out), background-color var(--dur-base) var(--ease-out)'
    }
  })));
}
Object.assign(__ds_scope, { VoiceBars });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/hud/VoiceBars.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/CornerBrackets.jsx
try { (() => {
function CornerBrackets({
  color = 'var(--fg-3)',
  activeColor = 'var(--red-400)',
  active = false,
  size = 8,
  activeSize,
  weight = 1,
  offset = -1,
  glow = true
}) {
  const s = active ? activeSize ?? size + 6 : size;
  const c = active ? activeColor : color;
  const base = {
    position: 'absolute',
    width: s,
    height: s,
    borderStyle: 'solid',
    borderColor: c,
    borderWidth: 0,
    pointerEvents: 'none',
    zIndex: 2,
    transition: 'width var(--dur-base) var(--ease-out), height var(--dur-base) var(--ease-out), border-color var(--dur-base) var(--ease-out), filter var(--dur-slow) var(--ease-out)',
    filter: active && glow ? 'drop-shadow(0 0 3px var(--red-500))' : 'none'
  };
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", {
    style: {
      ...base,
      top: offset,
      left: offset,
      borderTopWidth: weight,
      borderLeftWidth: weight
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      ...base,
      top: offset,
      right: offset,
      borderTopWidth: weight,
      borderRightWidth: weight
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      ...base,
      bottom: offset,
      left: offset,
      borderBottomWidth: weight,
      borderLeftWidth: weight
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      ...base,
      bottom: offset,
      right: offset,
      borderBottomWidth: weight,
      borderRightWidth: weight
    }
  }));
}
Object.assign(__ds_scope, { CornerBrackets });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/CornerBrackets.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  useRef,
  useState
} = React;
const SIZES = {
  sm: {
    h: 'var(--control-h-sm)',
    px: 8,
    fs: 9,
    icon: 10
  },
  md: {
    h: 'var(--control-h-md)',
    px: 12,
    fs: 10,
    icon: 12
  },
  lg: {
    h: 'var(--control-h-lg)',
    px: 16,
    fs: 11,
    icon: 13
  }
};
function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon,
  iconRight,
  disabled = false,
  fullWidth = false,
  type = 'button',
  onClick,
  style,
  ...rest
}) {
  const [hover, setHover] = useState(false);
  const [press, setPress] = useState(false);
  const ref = useRef(null);
  const s = SIZES[size] || SIZES.md;
  const h = hover && !disabled;
  const v = {
    primary: {
      background: press && h ? 'var(--accent-press)' : h ? 'var(--accent-hover)' : 'var(--accent)',
      color: 'var(--fg-on-accent)',
      border: '1px solid transparent',
      boxShadow: press && h ? 'var(--glow-red-xs)' : h ? 'var(--glow-red-md)' : 'var(--glow-red-xs)'
    },
    secondary: {
      background: 'transparent',
      color: h ? 'var(--fg-1)' : 'var(--fg-2)',
      border: `1px solid ${h ? 'var(--red-a40)' : 'var(--border-default)'}`,
      boxShadow: 'none'
    },
    ghost: {
      background: h ? 'var(--white-a04)' : 'transparent',
      color: h ? 'var(--fg-1)' : 'var(--fg-2)',
      border: '1px solid transparent',
      boxShadow: 'none'
    },
    rose: {
      background: h ? 'var(--rose-a08)' : 'transparent',
      color: 'var(--rose-200)',
      border: `1px solid ${h ? 'var(--rose-200)' : 'var(--rose-a32)'}`,
      boxShadow: h ? 'var(--glow-rose-sm)' : 'none'
    }
  }[variant];
  const glowColor = variant === 'rose' ? 'rgba(246,193,206,.18)' : variant === 'primary' ? 'rgba(255,255,255,.22)' : 'rgba(240,31,51,.28)';
  return /*#__PURE__*/React.createElement("button", _extends({
    ref: ref,
    type: type,
    disabled: disabled,
    onClick: onClick,
    onPointerEnter: () => setHover(true),
    onPointerLeave: () => {
      setHover(false);
      setPress(false);
    },
    onPointerDown: () => setPress(true),
    onPointerUp: () => setPress(false),
    onPointerMove: e => {
      const r = ref.current.getBoundingClientRect();
      ref.current.style.setProperty('--mx', `${e.clientX - r.left}px`);
      ref.current.style.setProperty('--my', `${e.clientY - r.top}px`);
    }
  }, rest, {
    style: {
      position: 'relative',
      display: fullWidth ? 'flex' : 'inline-flex',
      width: fullWidth ? '100%' : undefined,
      alignItems: 'center',
      justifyContent: 'center',
      gap: 6,
      height: s.h,
      padding: `0 ${s.px}px`,
      fontFamily: 'var(--font-sans)',
      fontWeight: 600,
      fontSize: s.fs,
      letterSpacing: 'var(--tracking-wider)',
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
      borderRadius: 'var(--radius-sm)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.35 : 1,
      overflow: variant === 'secondary' ? 'visible' : 'hidden',
      transform: press && h ? 'scale(.98)' : 'none',
      outlineOffset: 2,
      transition: 'var(--transition-color), transform var(--dur-instant) var(--ease-out)',
      ...v,
      ...style
    }
  }), variant !== 'ghost' && /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      opacity: h ? 1 : 0,
      background: `radial-gradient(70px circle at var(--mx,50%) var(--my,50%), ${glowColor}, transparent 70%)`,
      transition: 'opacity var(--dur-slow) var(--ease-out)'
    }
  }), variant === 'primary' && h && /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      position: 'absolute',
      top: 0,
      bottom: 0,
      left: 0,
      width: '45%',
      pointerEvents: 'none',
      background: 'var(--grad-red-sweep)',
      animation: 'groov-sweep 900ms var(--ease-out) 1'
    }
  }), variant === 'secondary' && /*#__PURE__*/React.createElement(__ds_scope.CornerBrackets, {
    active: h,
    color: "transparent",
    size: 0,
    activeSize: 6,
    offset: -1
  }), icon && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: s.icon,
    style: {
      position: 'relative'
    }
  }), children != null && /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'relative'
    }
  }, children), iconRight && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: iconRight,
    size: s.icon,
    style: {
      position: 'relative'
    }
  }));
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  useState
} = React;
const H = {
  sm: 'var(--control-h-sm)',
  md: 'var(--control-h-md)',
  lg: 'var(--control-h-lg)'
};
function Input({
  label,
  hint,
  error,
  icon,
  suffix,
  size = 'md',
  mono = false,
  disabled = false,
  value,
  defaultValue,
  onChange,
  placeholder,
  type = 'text',
  style,
  inputStyle,
  ...rest
}) {
  const [focus, setFocus] = useState(false);
  const [hover, setHover] = useState(false);
  const bad = !!error;
  const border = bad ? 'var(--red-400)' : focus ? 'var(--red-a40)' : hover && !disabled ? 'var(--border-strong)' : 'var(--border-default)';
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 5,
      minWidth: 0,
      opacity: disabled ? 0.4 : 1,
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wider)',
      textTransform: 'uppercase',
      color: focus ? 'var(--fg-1)' : 'var(--fg-3)',
      transition: 'var(--transition-color)'
    }
  }, label), /*#__PURE__*/React.createElement("span", {
    onPointerEnter: () => setHover(true),
    onPointerLeave: () => setHover(false),
    style: {
      position: 'relative',
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      height: H[size] || H.md,
      padding: '0 8px',
      background: focus ? 'var(--ink-100)' : 'var(--surface-sunken)',
      border: `1px solid ${border}`,
      borderRadius: 'var(--radius-xs)',
      boxShadow: focus ? 'var(--glow-inset-red)' : 'none',
      transition: 'var(--transition-color)',
      color: focus ? 'var(--red-400)' : 'var(--fg-3)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.CornerBrackets, {
    active: focus || bad,
    color: "transparent",
    size: 0,
    activeSize: 6
  }), icon && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 12
  }), /*#__PURE__*/React.createElement("input", _extends({
    type: type,
    value: value,
    defaultValue: defaultValue,
    onChange: onChange,
    placeholder: placeholder,
    disabled: disabled,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false)
  }, rest, {
    style: {
      flex: 1,
      minWidth: 0,
      height: '100%',
      background: 'transparent',
      border: 0,
      outline: 0,
      padding: 0,
      color: 'var(--fg-1)',
      caretColor: 'var(--red-400)',
      font: mono ? 'var(--type-data)' : 'var(--type-body)',
      fontSize: size === 'sm' ? 'var(--fs-xs)' : undefined,
      ...inputStyle
    }
  })), suffix && /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      color: 'var(--fg-3)',
      letterSpacing: 'var(--tracking-wide)'
    }
  }, suffix)), (error || hint) && /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wide)',
      color: bad ? 'var(--red-400)' : 'var(--fg-3)'
    }
  }, error || hint));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Panel.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  useRef,
  useState
} = React;
function Panel({
  eyebrow,
  meta,
  title,
  children,
  footer,
  onClose,
  actions,
  active = false,
  brackets = true,
  interactive = true,
  enter = true,
  delay = 0,
  padding = 'var(--panel-pad)',
  width,
  height,
  style,
  bodyStyle,
  ...rest
}) {
  const [hover, setHover] = useState(false);
  const ref = useRef(null);
  const lit = active || hover && interactive;
  const hasHeader = eyebrow || meta || onClose || actions;
  return /*#__PURE__*/React.createElement("section", _extends({
    ref: ref,
    onPointerEnter: () => setHover(true),
    onPointerLeave: () => setHover(false),
    onPointerMove: interactive ? e => {
      const r = ref.current.getBoundingClientRect();
      ref.current.style.setProperty('--mx', `${e.clientX - r.left}px`);
      ref.current.style.setProperty('--my', `${e.clientY - r.top}px`);
    } : undefined
  }, rest, {
    style: {
      position: 'relative',
      display: 'flex',
      flexDirection: 'column',
      width,
      height,
      minWidth: 0,
      background: 'var(--surface-panel)',
      backdropFilter: 'blur(var(--blur-panel))',
      WebkitBackdropFilter: 'blur(var(--blur-panel))',
      border: `1px solid ${active ? 'var(--red-a60)' : lit ? 'var(--red-a40)' : 'var(--border-default)'}`,
      boxShadow: active ? 'var(--glow-inset-red), var(--glow-red-sm)' : lit ? 'var(--glow-inset-red)' : 'none',
      transition: 'var(--transition-color)',
      animation: enter ? `groov-scale-in var(--dur-slow) var(--ease-out) ${delay}ms both` : 'none',
      ...style
    }
  }), interactive && /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      opacity: hover ? 1 : 0,
      background: 'radial-gradient(220px circle at var(--mx,50%) var(--my,50%), rgba(240,31,51,.10), transparent 70%)',
      transition: 'opacity var(--dur-slow) var(--ease-out)'
    }
  }), brackets && /*#__PURE__*/React.createElement(__ds_scope.CornerBrackets, {
    active: lit,
    color: "var(--fg-2)"
  }), hasHeader && /*#__PURE__*/React.createElement("header", {
    style: {
      position: 'relative',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      height: 'var(--panel-header-h)',
      padding: '0 4px 0 8px',
      borderBottom: '1px solid var(--border-subtle)',
      flex: 'none'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1,
      minWidth: 0,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wider)',
      textTransform: 'uppercase',
      color: lit ? 'var(--fg-2)' : 'var(--fg-3)',
      transition: 'var(--transition-color)'
    }
  }, eyebrow), meta && /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wide)',
      color: lit ? 'var(--red-400)' : 'var(--fg-3)',
      transition: 'var(--transition-color)'
    }
  }, meta), actions, onClose && /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    label: "Close",
    size: "sm",
    onClick: onClose,
    style: {
      width: 18,
      height: 18
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      flex: 1,
      minHeight: 0,
      padding,
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      ...bodyStyle
    }
  }, title && /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: 0,
      font: 'var(--type-heading)',
      textTransform: 'uppercase',
      color: 'var(--fg-1)',
      textWrap: 'pretty'
    }
  }, title), children), footer && /*#__PURE__*/React.createElement("footer", {
    style: {
      position: 'relative',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      padding: '6px 8px',
      borderTop: '1px solid var(--border-subtle)',
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wide)',
      color: 'var(--fg-3)'
    }
  }, footer));
}
Object.assign(__ds_scope, { Panel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Panel.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Dialog.jsx
try { (() => {
const {
  useEffect
} = React;
function Dialog({
  open,
  onClose,
  eyebrow,
  title,
  children,
  actions,
  width = 360
}) {
  useEffect(() => {
    if (!open) return;
    const k = e => {
      if (e.key === 'Escape' && onClose) onClose();
    };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [open, onClose]);
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    role: "dialog",
    "aria-modal": "true",
    onClick: onClose,
    style: {
      position: 'fixed',
      inset: 0,
      zIndex: 100,
      display: 'grid',
      placeItems: 'center',
      background: 'var(--surface-overlay)',
      backdropFilter: 'blur(var(--blur-overlay))',
      animation: 'groov-fade-in var(--dur-base) var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    onClick: e => e.stopPropagation(),
    style: {
      width,
      maxWidth: 'calc(100vw - 32px)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Panel, {
    active: true,
    eyebrow: eyebrow,
    onClose: onClose,
    title: title,
    interactive: false,
    style: {
      background: 'var(--ink-100)'
    },
    footer: actions ? /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 6,
        marginLeft: 'auto'
      }
    }, actions) : undefined
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      font: 'var(--type-body-sm)',
      color: 'var(--fg-2)'
    }
  }, children))));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Tabs.jsx
try { (() => {
const {
  useLayoutEffect,
  useRef,
  useState
} = React;
function Tabs({
  items = [],
  value,
  onChange,
  variant = 'line',
  style
}) {
  const refs = useRef({});
  const [bar, setBar] = useState({
    left: 0,
    width: 0
  });
  const [hov, setHov] = useState(null);
  const list = items.map(i => typeof i === 'string' ? {
    id: i,
    label: i
  } : i);
  useLayoutEffect(() => {
    const el = refs.current[value];
    if (el) setBar({
      left: el.offsetLeft,
      width: el.offsetWidth
    });
  }, [value, items.length]);
  const chips = variant === 'chips';
  return /*#__PURE__*/React.createElement("div", {
    role: "tablist",
    style: {
      position: 'relative',
      display: 'flex',
      gap: chips ? 4 : 18,
      borderBottom: chips ? 'none' : '1px solid var(--border-subtle)',
      ...style
    }
  }, list.map(t => {
    const on = t.id === value;
    const h = hov === t.id;
    return /*#__PURE__*/React.createElement("button", {
      key: t.id,
      ref: el => {
        refs.current[t.id] = el;
      },
      role: "tab",
      "aria-selected": on,
      type: "button",
      onClick: () => onChange && onChange(t.id),
      onPointerEnter: () => setHov(t.id),
      onPointerLeave: () => setHov(null),
      style: {
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        height: chips ? 20 : 26,
        padding: chips ? '0 8px' : 0,
        cursor: 'pointer',
        font: 'var(--type-label)',
        fontSize: chips ? 'var(--fs-micro)' : 'var(--fs-2xs)',
        letterSpacing: 'var(--tracking-wider)',
        textTransform: 'uppercase',
        color: on ? 'var(--fg-1)' : h ? 'var(--fg-1)' : 'var(--fg-3)',
        background: chips ? on ? 'var(--red-a14)' : 'transparent' : 'transparent',
        border: chips ? `1px solid ${on ? 'var(--red-500)' : h ? 'var(--border-strong)' : 'var(--border-default)'}` : 0,
        borderRadius: chips ? 'var(--radius-sm)' : 0,
        boxShadow: chips && on ? 'var(--glow-red-xs)' : 'none',
        transition: 'var(--transition-color)'
      }
    }, t.label, t.count != null && /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-micro)',
        color: on ? 'var(--red-400)' : 'var(--fg-3)'
      }
    }, t.count));
  }), !chips && /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      position: 'absolute',
      bottom: -1,
      height: 1,
      left: bar.left,
      width: bar.width,
      background: 'var(--red-400)',
      boxShadow: '0 0 6px var(--red-500), 0 0 12px var(--red-500)',
      transition: 'left var(--dur-slow) var(--ease-out), width var(--dur-slow) var(--ease-out)'
    }
  }));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Tabs.jsx", error: String((e && e.message) || e) }); }

// ui_kits/groov-hud/App.jsx
try { (() => {
const AppDS = window.ROSEHUDDesignSystem_bed3b4;
const ROSE_QUERY = 'Research Meta Quest — sales, top genres, what ships next. Be specific.';
const ROSE_REPLY = 'Ten panels up. Short version: about 20 million sold, and social, sandbox and fitness titles keep people coming back.';
const stamp = () => new Date().toTimeString().slice(0, 5);
function IdleView() {
  const {
    Panel,
    Progress
  } = AppDS;
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: '50%',
      top: '50%',
      width: 520,
      height: 520,
      transform: 'translate(-50%,-50%)',
      background: 'var(--grad-core)',
      opacity: 0.5,
      animation: 'groov-pulse 4s var(--ease-in-out) infinite'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: '50%',
      top: '50%',
      transform: 'translate(-50%,-50%)',
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-widest)',
      color: 'var(--fg-3)',
      whiteSpace: 'nowrap',
      animation: 'groov-fade-up .8s var(--ease-out)'
    }
  }, "PRESS SPACE OR TAP THE CORE TO TALK", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--red-400)',
      animation: 'groov-blink 1s steps(1) infinite'
    }
  }, " _")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      top: '54%',
      width: 230
    }
  }, /*#__PURE__*/React.createElement(Panel, {
    eyebrow: "Last session",
    meta: "#S-041",
    title: "Meta Quest \u2014 late 2025: real hits, hard limits",
    footer: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", null, "64% reviewed"), /*#__PURE__*/React.createElement("span", {
      style: {
        marginLeft: 'auto'
      }
    }, "10 panels"))
  }, /*#__PURE__*/React.createElement(Progress, {
    size: "sm",
    value: 64,
    showValue: false
  }))));
}
function ThinkView({
  phase,
  text
}) {
  const {
    StatusDot
  } = AppDS;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'grid',
      placeItems: 'center',
      animation: 'groov-fade-in .5s var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 28
    }
  }, /*#__PURE__*/React.createElement(CoreRings, {
    size: 340,
    mode: phase
  }), /*#__PURE__*/React.createElement(StatusDot, {
    tone: phase === 'listening' ? 'live' : 'online',
    label: phase === 'listening' ? 'Listening...' : 'Pulling sources...'
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 520,
      minHeight: 18,
      textAlign: 'center',
      font: 'var(--type-data)',
      fontSize: 'var(--fs-xs)',
      color: 'var(--fg-1)'
    }
  }, text)));
}
function App() {
  const {
    Dialog,
    Button,
    Toast,
    Input,
    IconButton
  } = AppDS;
  const start = window.ROSE_START || 'dashboard';
  const dash = start === 'dashboard';
  const [phase, setPhase] = React.useState(start);
  const [chips, setChips] = React.useState({
    history: dash,
    text: false,
    camera: false
  });
  const [voice, setVoice] = React.useState('Groov — warm');
  const [panels, setPanels] = React.useState(dash ? DASH_PANELS.map(p => p.id) : []);
  const [activeId, setActiveId] = React.useState(dash ? 'sold' : null);
  const [strip, setStrip] = React.useState({
    who: 'YOU',
    text: 'No, please. Go, please proceed! Be specific',
    speaking: false
  });
  const [turns, setTurns] = React.useState(dash ? [{
    who: 'YOU',
    time: '21:02',
    text: ROSE_QUERY
  }, {
    who: 'GROOV',
    time: '21:02',
    text: ROSE_REPLY
  }, {
    who: 'YOU',
    time: '21:04',
    text: 'No, please. Go, please proceed! Be specific'
  }] : []);
  const [confirm, setConfirm] = React.useState(false);
  const [toast, setToast] = React.useState(null);
  const [draft, setDraft] = React.useState('');
  const timers = React.useRef([]);
  const phaseRef = React.useRef(phase);
  phaseRef.current = phase;
  const later = (fn, ms) => timers.current.push(setTimeout(fn, ms));
  const talk = (q = ROSE_QUERY) => {
    if (['listening', 'thinking', 'boot'].includes(phaseRef.current)) return;
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setPhase('listening');
    setActiveId(null);
    setToast(null);
    let n = 0;
    setStrip({
      who: 'YOU',
      text: '',
      speaking: true
    });
    const step = () => {
      n += 2;
      setStrip({
        who: 'YOU',
        text: q.slice(0, n),
        speaking: true
      });
      if (n < q.length) return later(step, 35);
      later(() => {
        setTurns(t => [...t, {
          who: 'YOU',
          time: stamp(),
          text: q
        }]);
        setPhase('thinking');
        setStrip({
          who: 'GROOV',
          text: 'Pulling sources...',
          speaking: true
        });
        later(() => {
          setPanels(DASH_PANELS.map(p => p.id));
          setPhase('dashboard');
          setActiveId('sold');
          setStrip({
            who: 'GROOV',
            text: ROSE_REPLY,
            speaking: true
          });
          setTurns(t => [...t, {
            who: 'GROOV',
            time: stamp(),
            text: ROSE_REPLY
          }]);
          setChips(c => ({
            ...c,
            history: true
          }));
          setToast({
            title: '10 panels',
            message: 'Research canvas ready.'
          });
          later(() => setStrip(s => ({
            ...s,
            speaking: false
          })), 2800);
        }, 1600);
      }, 500);
    };
    later(step, 500);
  };
  React.useEffect(() => {
    const k = e => {
      if (e.code === 'Space' && e.target === document.body) {
        e.preventDefault();
        talk();
      }
    };
    window.addEventListener('keydown', k);
    return () => {
      window.removeEventListener('keydown', k);
      timers.current.forEach(clearTimeout);
    };
  }, []);
  const onChip = id => {
    if (id === 'clear') {
      if (panels.length) setConfirm(true);
      return;
    }
    setChips(c => ({
      ...c,
      [id]: !c[id]
    }));
  };
  const clearAll = () => {
    setPanels([]);
    setActiveId(null);
    setConfirm(false);
    setPhase('idle');
    setChips(c => ({
      ...c,
      camera: false
    }));
  };
  const closePanel = id => setPanels(ps => {
    const nx = ps.filter(x => x !== id);
    if (!nx.length) setPhase('idle');
    return nx;
  });
  const send = () => {
    if (!draft.trim()) return;
    const q = draft.trim();
    setDraft('');
    talk(q);
  };
  if (phase === 'boot') return /*#__PURE__*/React.createElement(BootScreen, {
    onDone: () => setPhase('idle')
  });
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      backgroundImage: 'var(--bg-grid)',
      backgroundSize: 'var(--bg-grid-size)',
      WebkitMaskImage: 'radial-gradient(ellipse at center, #000 20%, transparent 75%)',
      maskImage: 'radial-gradient(ellipse at center, #000 20%, transparent 75%)',
      opacity: 0.7
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: 'var(--grad-vignette)',
      pointerEvents: 'none'
    }
  }), /*#__PURE__*/React.createElement(HudTopLeft, {
    phase: phase,
    onReboot: () => setPhase('boot')
  }), /*#__PURE__*/React.createElement(HudTopRight, {
    chips: {
      ...chips,
      clear: confirm
    },
    onChip: onChip,
    voice: voice,
    onVoice: setVoice
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 48,
      left: 22,
      right: 22,
      bottom: 52,
      display: 'grid',
      gridTemplateColumns: chips.history ? 'minmax(0,1fr) 250px' : 'minmax(0,1fr)',
      gap: 14
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      minHeight: 0,
      minWidth: 0
    }
  }, phase === 'dashboard' && /*#__PURE__*/React.createElement(Dashboard, {
    panels: panels,
    activeId: activeId,
    onActivate: setActiveId,
    onClose: closePanel,
    camera: chips.camera
  }), phase === 'idle' && /*#__PURE__*/React.createElement(IdleView, null), (phase === 'listening' || phase === 'thinking') && /*#__PURE__*/React.createElement(ThinkView, {
    phase: phase,
    text: strip.text
  })), chips.history && /*#__PURE__*/React.createElement("div", {
    style: {
      minHeight: 0,
      display: 'flex',
      flexDirection: 'column',
      paddingBottom: 96
    }
  }, /*#__PURE__*/React.createElement(TranscriptColumn, {
    turns: turns
  }))), /*#__PURE__*/React.createElement(TranscriptStrip, {
    who: strip.who,
    text: strip.text,
    speaking: strip.speaking
  }), chips.text && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: '50%',
      bottom: 56,
      transform: 'translateX(-50%)',
      width: 440,
      display: 'flex',
      gap: 6,
      alignItems: 'center',
      zIndex: 7,
      animation: 'groov-fade-up var(--dur-slow) var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement(Input, {
    value: draft,
    onChange: e => setDraft(e.target.value),
    onKeyDown: e => e.key === 'Enter' && send(),
    placeholder: "Type to GROOV\u2026",
    icon: "type",
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement(IconButton, {
    icon: "send",
    label: "Send",
    variant: "solid",
    onClick: send
  })), /*#__PURE__*/React.createElement(CornerOrb, {
    phase: phase,
    onClick: () => talk()
  }), toast && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 22,
      bottom: 48,
      zIndex: 8
    }
  }, /*#__PURE__*/React.createElement(Toast, {
    icon: "layout-grid",
    title: toast.title,
    message: toast.message,
    tone: "rose",
    duration: 3500,
    onClose: () => setToast(null)
  })), /*#__PURE__*/React.createElement(Dialog, {
    open: confirm,
    onClose: () => setConfirm(false),
    eyebrow: "System",
    title: "Clear all panels?",
    actions: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      size: "sm",
      onClick: () => setConfirm(false)
    }, "Cancel"), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      onClick: clearAll
    }, "Clear"))
  }, "Removes ", panels.length, " panels from the canvas. Transcript is kept."));
}
ReactDOM.createRoot(document.getElementById('root')).render(/*#__PURE__*/React.createElement(App, null));
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/groov-hud/App.jsx", error: String((e && e.message) || e) }); }

// ui_kits/groov-hud/BootScreen.jsx
try { (() => {
const BootDS = window.ROSEHUDDesignSystem_bed3b4;
const BOOT_STEPS = [{
  at: 0,
  phase: 'cross'
}, {
  at: 700,
  phase: 'rings'
}, {
  at: 1500,
  phase: 'load',
  v: 18,
  l: 'Iniciando sistema...'
}, {
  at: 2500,
  phase: 'load',
  v: 47,
  l: 'Carregando módulos...'
}, {
  at: 3500,
  phase: 'load',
  v: 87,
  l: 'Finalizando inicialização...'
}, {
  at: 4300,
  phase: 'load',
  v: 100,
  l: 'Finalizando inicialização...'
}, {
  at: 4900,
  phase: 'online'
}, {
  at: 7200,
  phase: 'done'
}];
function BootScreen({
  onDone
}) {
  const {
    Reticle,
    Progress,
    StatusDot,
    CornerBrackets,
    Button
  } = BootDS;
  const [i, setI] = React.useState(0);
  React.useEffect(() => {
    const ts = BOOT_STEPS.map((s, k) => setTimeout(() => s.phase === 'done' ? onDone() : setI(k), s.at));
    return () => ts.forEach(clearTimeout);
  }, []);
  const s = BOOT_STEPS[i];
  const ph = s.phase;
  const tick = {
    position: 'absolute',
    top: 'calc(50% - 14px)',
    width: 1,
    height: 28,
    background: 'var(--red-500)',
    boxShadow: 'var(--glow-red-sm)',
    animation: 'groov-flicker .8s linear both'
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'grid',
      placeItems: 'center',
      background: 'var(--bg-void)',
      animation: 'groov-fade-in .4s var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 28
    }
  }, /*#__PURE__*/React.createElement(CornerBrackets, {
    size: 28,
    color: "var(--fg-3)"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: '4%',
      right: '4%',
      top: '50%',
      height: 1,
      background: 'linear-gradient(90deg,transparent,var(--white-a12) 20%,var(--white-a12) 80%,transparent)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: '6%',
      bottom: '6%',
      left: '50%',
      width: 1,
      background: 'linear-gradient(180deg,transparent,var(--white-a04),transparent)'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      ...tick,
      left: '4%'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      ...tick,
      right: '4%'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 22
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      transform: ph === 'cross' ? 'scale(.82)' : 'none',
      opacity: ph === 'cross' ? 0.6 : 1,
      transition: 'all .9s var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement(Reticle, {
    size: 260,
    state: ph === 'cross' ? 'off' : ph === 'online' ? 'listening' : 'idle',
    ticks: ph !== 'cross',
    view: ph === 'online' ? '3d' : '2d',
    ringText: ph === 'online' ? 'GROOV // CORE 01 // ONLINE' : undefined
  }, ph === 'cross' ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: '200 22px var(--font-sans)',
      color: 'var(--fg-3)'
    }
  }, "+") : /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 6,
      animation: 'groov-flicker 1.1s linear both'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-display)',
      letterSpacing: '.08em',
      color: 'var(--fg-1)',
      textShadow: 'var(--text-glow-white)'
    }
  }, "GROOV"), /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      letterSpacing: '2px',
      color: 'var(--fg-3)'
    }
  }, "///")))), /*#__PURE__*/React.createElement("div", {
    style: {
      height: 52,
      width: 340,
      display: 'grid',
      placeItems: 'center'
    }
  }, ph === 'load' && /*#__PURE__*/React.createElement("div", {
    style: {
      width: '100%',
      animation: 'groov-fade-up .4s var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement(Progress, {
    label: s.l,
    value: s.v
  })), ph === 'online' && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 14,
      animation: 'groov-fade-up .6s var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement(StatusDot, {
    tone: "online",
    label: "Online",
    bracketed: true,
    pulse: false,
    size: 0
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8
    }
  }, [0, 1, 2].map(d => /*#__PURE__*/React.createElement("span", {
    key: d,
    style: {
      width: 4,
      height: 4,
      borderRadius: '50%',
      background: d === 0 ? 'var(--red-500)' : 'var(--ink-500)',
      boxShadow: d === 0 ? 'var(--glow-red-sm)' : 'none'
    }
  })))))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      right: 44,
      bottom: 40
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "ghost",
    size: "sm",
    iconRight: "skip-forward",
    onClick: onDone
  }, "Skip")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 44,
      bottom: 44,
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wider)',
      color: 'var(--fg-3)'
    }
  }, "GROOV // CORE 01 \xB7 BOOT ", String(i).padStart(2, '0'), "/06"));
}
window.BootScreen = BootScreen;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/groov-hud/BootScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/groov-hud/CoreRings.jsx
try { (() => {
function CoreRings({
  size = 340,
  mode = 'listening'
}) {
  const fast = mode === 'thinking' ? 0.4 : 1;
  const stage = React.useRef(null);
  React.useEffect(() => {
    const mv = e => {
      if (!stage.current) return;
      const px = e.clientX / window.innerWidth - 0.5;
      const py = e.clientY / window.innerHeight - 0.5;
      stage.current.style.transform = `rotateX(${-py * 30}deg) rotateY(${px * 40}deg) rotateZ(-24deg)`;
    };
    window.addEventListener('pointermove', mv);
    return () => window.removeEventListener('pointermove', mv);
  }, []);
  const rings = [{
    inset: '6%',
    ry: 64,
    rx: 8,
    w: 1.5,
    c: 'var(--fg-1)',
    dur: 6,
    glow: '0 0 6px rgba(255,255,255,.35)'
  }, {
    inset: '18%',
    ry: 58,
    rx: -14,
    w: 2.5,
    c: 'var(--red-500)',
    dur: 3.2,
    glow: '0 0 10px var(--red-500), 0 0 28px rgba(240,31,51,.5)',
    rev: true
  }, {
    inset: '28%',
    ry: 70,
    rx: 22,
    w: 1,
    c: 'var(--rose-200)',
    dur: 4.5,
    glow: 'none'
  }, {
    inset: '2%',
    ry: 76,
    rx: -6,
    w: 1,
    c: 'var(--white-a32)',
    dur: 9,
    glow: 'none',
    rev: true
  }];
  const gyros = [{
    inset: '10%',
    c: 'var(--fg-1)',
    w: 1,
    dur: 7,
    anim: 'groov-gyro',
    tilt: 'rotateZ(20deg)'
  }, {
    inset: '22%',
    c: 'var(--red-400)',
    w: 1.5,
    dur: 5,
    anim: 'groov-gyro-x',
    tilt: 'rotateZ(-35deg)',
    glow: '0 0 8px var(--red-500)'
  }];
  const dots = React.useMemo(() => Array.from({
    length: 22
  }, (_, i) => {
    const a = i / 22 * Math.PI * 2;
    const r = 0.42 + i * 37 % 10 / 60;
    return {
      x: 50 + Math.cos(a) * r * 100 * 0.9,
      y: 50 + Math.sin(a) * r * 100 * 0.5,
      d: i % 6 * 0.3,
      s: 1 + i % 3
    };
  }), []);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      width: size,
      height: size,
      perspective: 900
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: '20%',
      borderRadius: '50%',
      background: 'var(--grad-core)',
      animation: 'groov-pulse var(--dur-pulse) var(--ease-in-out) infinite'
    }
  }), /*#__PURE__*/React.createElement("div", {
    ref: stage,
    style: {
      position: 'absolute',
      inset: 0,
      transformStyle: 'preserve-3d',
      transform: 'rotateZ(-24deg)',
      transition: 'transform 1.4s var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      transformStyle: 'preserve-3d',
      animation: `groov-wobble ${7 * fast}s var(--ease-in-out) infinite`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: '-25%',
      right: '-25%',
      top: '50%',
      height: 1.5,
      background: 'linear-gradient(90deg,transparent,var(--red-500) 30%,var(--red-300) 50%,var(--red-500) 70%,transparent)',
      boxShadow: '0 0 8px var(--red-500)'
    }
  }), rings.map((r, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      position: 'absolute',
      inset: r.inset,
      transformStyle: 'preserve-3d',
      transform: `rotateY(${r.ry}deg) rotateX(${r.rx}deg)`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: '50%',
      borderStyle: 'solid',
      borderWidth: r.w,
      borderColor: `${r.c} ${r.c} transparent ${r.c}`,
      boxShadow: r.glow,
      animation: `${r.rev ? 'groov-spin-rev' : 'groov-spin'} ${r.dur * fast}s linear infinite`
    }
  }))), gyros.map((g, i) => /*#__PURE__*/React.createElement("div", {
    key: `g${i}`,
    style: {
      position: 'absolute',
      inset: g.inset,
      transformStyle: 'preserve-3d',
      transform: g.tilt
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: '50%',
      border: `${g.w}px dashed ${g.c}`,
      boxShadow: g.glow || 'none',
      opacity: 0.7,
      animation: `${g.anim} ${g.dur * fast}s linear infinite`
    }
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      animation: `groov-spin ${14 * fast}s linear infinite`
    }
  }, dots.map((d, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      position: 'absolute',
      left: `${d.x}%`,
      top: `${d.y}%`,
      width: d.s,
      height: d.s,
      background: i % 4 === 0 ? 'var(--red-400)' : 'var(--fg-2)',
      borderRadius: '50%',
      animation: `groov-pulse 1.8s var(--ease-in-out) ${d.d}s infinite`
    }
  }))))));
}
window.CoreRings = CoreRings;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/groov-hud/CoreRings.jsx", error: String((e && e.message) || e) }); }

// ui_kits/groov-hud/Dashboard.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const DashDS = window.ROSEHUDDesignSystem_bed3b4;
const DASH_PANELS = [{
  id: 'clip',
  area: '1 / 1 / 3 / 2',
  eyebrow: 'Clip · Short-form',
  meta: '#A-101',
  media: 'Vertical clip',
  play: true
}, {
  id: 'ship',
  area: '1 / 2 / 2 / 3',
  eyebrow: 'Source · Press',
  meta: '#A-102',
  title: 'Meta Quest 3S / Quest 3 — shipping',
  body: 'Quest 3S takes the entry tier; Quest 3 stays as the premium model. Same store, same controllers, same account.'
}, {
  id: 'hits',
  area: '1 / 3 / 2 / 4',
  eyebrow: 'Analysis',
  meta: '#A-103',
  title: 'Hits: social, sandbox, fitness and rhythm',
  body: 'The titles that keep headsets in use are social hangouts, sandbox builders, fitness and rhythm games. Short sessions, repeat play.'
}, {
  id: 'product',
  area: '1 / 4 / 3 / 5',
  eyebrow: 'Media · Product',
  meta: '#A-104',
  media: 'Product image',
  caption: 'Headset + controllers, front three-quarter.'
}, {
  id: 'base',
  area: '2 / 2 / 3 / 3',
  eyebrow: 'Data · Sample',
  meta: '#A-105',
  title: 'Headsets in use, by year',
  chart: [{
    label: '21',
    value: 6
  }, {
    label: '22',
    value: 11
  }, {
    label: '23',
    value: 14
  }, {
    label: '24',
    value: 17
  }, {
    label: '25',
    value: 20
  }]
}, {
  id: 'payload',
  area: '2 / 3 / 3 / 4',
  eyebrow: 'System',
  meta: '#A-106',
  title: 'Working payload: text, thumbnail, image, editable',
  code: ['panel.type     = "brief"', 'panel.sources  = 3', 'panel.media    = ["thumb", "image"]', 'panel.editable = true']
}, {
  id: 'genres',
  area: '3 / 1 / 4 / 2',
  eyebrow: 'Data · Sample',
  meta: '#A-107',
  title: 'Top genres by hours',
  chart: [{
    label: 'Soc',
    value: 34
  }, {
    label: 'Sbx',
    value: 22
  }, {
    label: 'Fit',
    value: 18
  }, {
    label: 'Rhy',
    value: 12
  }, {
    label: 'Oth',
    value: 8
  }]
}, {
  id: 'bands',
  area: '3 / 2 / 4 / 3',
  eyebrow: 'Data · Sample',
  meta: '#A-108',
  title: 'Three bands used, three auth models',
  chart: [{
    label: 'Low',
    value: 9
  }, {
    label: 'Mid',
    value: 14
  }, {
    label: 'High',
    value: 5
  }],
  highlight: 1
}, {
  id: 'sold',
  area: '3 / 3 / 4 / 4',
  eyebrow: 'Figure',
  meta: '#A-109',
  stat: {
    prefix: '≈',
    value: 20,
    suffix: 'm',
    label: 'Quest headsets sold',
    caption: 'Cumulatively by early 2025, as reported.'
  }
}, {
  id: 'build',
  area: '3 / 4 / 4 / 5',
  eyebrow: 'Runtime',
  meta: '#A-110',
  stat: {
    value: '27.15.0',
    label: 'Runtime build',
    caption: 'Uptime 72 h 16 · 10 panels'
  }
}];
function MediaBox({
  label,
  play
}) {
  const {
    IconButton
  } = DashDS;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      flex: 1,
      minHeight: 60,
      display: 'grid',
      placeItems: 'center',
      background: 'var(--white-a04)',
      border: '1px solid var(--border-subtle)',
      backgroundImage: 'var(--bg-scanlines)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wider)',
      color: 'var(--fg-3)',
      textTransform: 'uppercase'
    }
  }, label), play && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 8,
      bottom: 8
    }
  }, /*#__PURE__*/React.createElement(IconButton, {
    icon: "play",
    label: "Play",
    size: "sm",
    variant: "outline"
  })));
}
function DashPanel({
  p,
  i,
  active,
  onActivate,
  onClose
}) {
  const {
    Panel,
    BarChart,
    Stat
  } = DashDS;
  const body = {
    margin: 0,
    font: 'var(--type-body-sm)',
    color: 'var(--fg-2)',
    textWrap: 'pretty'
  };
  return /*#__PURE__*/React.createElement(Panel, {
    eyebrow: p.eyebrow,
    meta: p.meta,
    title: p.title,
    onClose: () => onClose(p.id),
    active: active,
    delay: i * 55,
    onClick: () => onActivate(p.id),
    bodyStyle: {
      overflow: 'hidden'
    },
    style: {
      gridArea: p.area,
      minHeight: 0,
      overflow: 'hidden',
      cursor: 'default'
    },
    footer: p.chart ? /*#__PURE__*/React.createElement("span", null, "SAMPLE DATA \xB7 ILLUSTRATIVE") : undefined
  }, p.body && /*#__PURE__*/React.createElement("p", {
    style: body
  }, p.body), p.media && /*#__PURE__*/React.createElement(MediaBox, {
    label: p.media,
    play: p.play
  }), p.caption && /*#__PURE__*/React.createElement("p", {
    style: {
      ...body,
      fontSize: 'var(--fs-2xs)'
    }
  }, p.caption), p.chart && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'auto'
    }
  }, /*#__PURE__*/React.createElement(BarChart, {
    data: p.chart,
    height: 64,
    highlight: p.highlight ?? 'max'
  })), p.code && /*#__PURE__*/React.createElement("pre", {
    style: {
      margin: 0,
      padding: 8,
      background: 'var(--surface-sunken)',
      border: '1px solid var(--border-subtle)',
      font: 'var(--type-data)',
      fontSize: 'var(--fs-2xs)',
      color: 'var(--fg-2)',
      whiteSpace: 'pre-wrap'
    }
  }, p.code.join('\n')), p.stat && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'auto'
    }
  }, /*#__PURE__*/React.createElement(Stat, _extends({}, p.stat, {
    size: typeof p.stat.value === 'number' ? 'lg' : 'sm'
  }))));
}
function Dashboard({
  panels,
  activeId,
  onActivate,
  onClose,
  camera
}) {
  const {
    Panel,
    StatusDot
  } = DashDS;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      height: '100%',
      display: 'grid',
      gridTemplateColumns: 'repeat(4, minmax(0,1fr))',
      gridTemplateRows: 'repeat(3, minmax(0,1fr))',
      gap: 14
    }
  }, DASH_PANELS.filter(p => panels.includes(p.id)).map((p, i) => /*#__PURE__*/React.createElement(DashPanel, {
    key: p.id,
    p: p,
    i: i,
    active: activeId === p.id,
    onActivate: onActivate,
    onClose: onClose
  })), camera && /*#__PURE__*/React.createElement(Panel, {
    eyebrow: "Camera \xB7 Feed",
    meta: "LIVE",
    interactive: false,
    style: {
      position: 'absolute',
      left: '50%',
      top: '50%',
      width: 260,
      height: 180,
      transform: 'translate(-50%,-50%)',
      zIndex: 4,
      background: 'var(--ink-100)'
    },
    actions: /*#__PURE__*/React.createElement(StatusDot, {
      tone: "live",
      size: 4
    })
  }, /*#__PURE__*/React.createElement(MediaBox, {
    label: "Camera feed"
  })));
}
Object.assign(window, {
  Dashboard,
  DASH_PANELS,
  MediaBox
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/groov-hud/Dashboard.jsx", error: String((e && e.message) || e) }); }

// ui_kits/groov-hud/HudChrome.jsx
try { (() => {
const ChromeDS = window.ROSEHUDDesignSystem_bed3b4;
function HudTopLeft({
  phase,
  onReboot
}) {
  const {
    StatusDot
  } = ChromeDS;
  const [now, setNow] = React.useState(new Date());
  React.useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  const label = {
    idle: 'Online',
    listening: 'Listening',
    thinking: 'Thinking',
    dashboard: 'Online'
  }[phase] || 'Online';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 18,
      left: 22,
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      zIndex: 5
    }
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: onReboot,
    title: "Replay boot",
    style: {
      padding: 0,
      background: 'none',
      border: 0,
      cursor: 'pointer',
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-widest)',
      color: 'var(--fg-rose)'
    }
  }, "GROOV // CORE 01"), /*#__PURE__*/React.createElement(StatusDot, {
    tone: phase === 'listening' ? 'live' : 'online',
    label: label,
    size: 5
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wide)',
      color: 'var(--fg-3)',
      fontVariantNumeric: 'tabular-nums'
    }
  }, now.toTimeString().slice(0, 8)));
}
function HudTopRight({
  chips,
  onChip,
  voice,
  onVoice
}) {
  const {
    Tag,
    Select
  } = ChromeDS;
  const items = [['history', 'History'], ['text', 'Text'], ['clear', 'Clear text'], ['camera', 'Camera']];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 14,
      right: 18,
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      zIndex: 5
    }
  }, items.map(([id, l]) => /*#__PURE__*/React.createElement(Tag, {
    key: id,
    selected: !!chips[id],
    onClick: () => onChip(id)
  }, l)), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 8
    }
  }), /*#__PURE__*/React.createElement(Select, {
    size: "sm",
    value: voice,
    onChange: onVoice,
    width: 170,
    options: ['Groov — warm', 'Groov — neutral', 'Groov — fast']
  }));
}
function TranscriptStrip({
  who,
  text,
  speaking
}) {
  const {
    VoiceBars,
    Badge
  } = ChromeDS;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 22,
      bottom: 20,
      right: 180,
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      zIndex: 5,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement(VoiceBars, {
    active: speaking,
    count: 16,
    height: 14,
    tone: who === 'GROOV' ? 'red' : 'white'
  }), /*#__PURE__*/React.createElement(Badge, {
    tone: who === 'GROOV' ? 'red' : 'neutral'
  }, who), /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-data)',
      fontSize: 'var(--fs-2xs)',
      color: 'var(--fg-1)',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis'
    }
  }, text, speaking && /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--red-400)',
      animation: 'groov-blink 1s steps(1) infinite'
    }
  }, "\u258D")));
}
function CornerOrb({
  phase,
  onClick
}) {
  const {
    Reticle
  } = ChromeDS;
  const [hover, setHover] = React.useState(false);
  const st = phase === 'listening' ? 'listening' : phase === 'thinking' ? 'thinking' : 'online';
  return /*#__PURE__*/React.createElement("button", {
    type: "button",
    "aria-label": "Talk to GROOV",
    onClick: onClick,
    onPointerEnter: () => setHover(true),
    onPointerLeave: () => setHover(false),
    style: {
      position: 'absolute',
      right: 14,
      bottom: 10,
      padding: 0,
      background: 'none',
      border: 0,
      cursor: 'pointer',
      zIndex: 6,
      transform: hover ? 'scale(1.05)' : 'none',
      transition: 'transform var(--dur-slow) var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement(Reticle, {
    size: 130,
    state: st,
    tone: "rose",
    view: hover || st !== 'online' ? '3d' : '2d',
    ringText: "GROOV // CORE 01"
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-display)',
      fontSize: 'var(--fs-md)',
      letterSpacing: '.08em',
      color: 'var(--fg-1)',
      textShadow: hover ? 'var(--text-glow-red)' : 'var(--text-glow-white)',
      transition: 'text-shadow var(--dur-slow) var(--ease-out)'
    }
  }, "GROOV")));
}
Object.assign(window, {
  HudTopLeft,
  HudTopRight,
  TranscriptStrip,
  CornerOrb
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/groov-hud/HudChrome.jsx", error: String((e && e.message) || e) }); }

// ui_kits/groov-hud/TranscriptColumn.jsx
try { (() => {
const TxDS = window.ROSEHUDDesignSystem_bed3b4;
function TranscriptColumn({
  turns
}) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [turns.length]);
  return /*#__PURE__*/React.createElement("aside", {
    style: {
      position: 'relative',
      display: 'flex',
      flexDirection: 'column',
      minHeight: 0,
      borderLeft: '1px solid var(--border-subtle)',
      background: 'rgba(5,5,6,.6)',
      animation: 'groov-fade-in var(--dur-slow) var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      height: 'var(--panel-header-h)',
      padding: '0 12px',
      borderBottom: '1px solid var(--border-subtle)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wider)',
      color: 'var(--fg-3)'
    }
  }, "TRANSCRIPT"), /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      color: 'var(--fg-3)'
    }
  }, turns.length)), /*#__PURE__*/React.createElement("div", {
    ref: ref,
    style: {
      flex: 1,
      minHeight: 0,
      overflowY: 'auto',
      padding: 12,
      display: 'flex',
      flexDirection: 'column',
      gap: 14
    }
  }, turns.map((t, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      animation: 'groov-fade-up var(--dur-slow) var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      letterSpacing: 'var(--tracking-wider)',
      color: t.who === 'GROOV' ? 'var(--red-400)' : 'var(--fg-2)'
    }
  }, t.who), /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-micro)',
      color: 'var(--fg-3)'
    }
  }, t.time)), /*#__PURE__*/React.createElement("div", {
    style: {
      font: 'var(--type-data)',
      fontSize: 'var(--fs-2xs)',
      lineHeight: 1.55,
      color: t.who === 'GROOV' ? 'var(--fg-1)' : 'var(--fg-2)',
      textWrap: 'pretty'
    }
  }, t.text)))));
}
window.TranscriptColumn = TranscriptColumn;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/groov-hud/TranscriptColumn.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.Tooltip = __ds_scope.Tooltip;

__ds_ns.Progress = __ds_scope.Progress;

__ds_ns.StatusDot = __ds_scope.StatusDot;

__ds_ns.Toast = __ds_scope.Toast;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Radio = __ds_scope.Radio;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.BarChart = __ds_scope.BarChart;

__ds_ns.Reticle = __ds_scope.Reticle;

__ds_ns.Stat = __ds_scope.Stat;

__ds_ns.VoiceBars = __ds_scope.VoiceBars;

__ds_ns.CornerBrackets = __ds_scope.CornerBrackets;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.Panel = __ds_scope.Panel;

__ds_ns.Tabs = __ds_scope.Tabs;

})();
