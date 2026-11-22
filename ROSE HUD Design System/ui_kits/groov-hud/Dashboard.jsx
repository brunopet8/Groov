const DashDS = window.ROSEHUDDesignSystem_bed3b4;

const DASH_PANELS = [
  { id: 'clip', area: '1 / 1 / 3 / 2', eyebrow: 'Clip · Short-form', meta: '#A-101', media: 'Vertical clip', play: true },
  { id: 'ship', area: '1 / 2 / 2 / 3', eyebrow: 'Source · Press', meta: '#A-102', title: 'Meta Quest 3S / Quest 3 — shipping',
    body: 'Quest 3S takes the entry tier; Quest 3 stays as the premium model. Same store, same controllers, same account.' },
  { id: 'hits', area: '1 / 3 / 2 / 4', eyebrow: 'Analysis', meta: '#A-103', title: 'Hits: social, sandbox, fitness and rhythm',
    body: 'The titles that keep headsets in use are social hangouts, sandbox builders, fitness and rhythm games. Short sessions, repeat play.' },
  { id: 'product', area: '1 / 4 / 3 / 5', eyebrow: 'Media · Product', meta: '#A-104', media: 'Product image', caption: 'Headset + controllers, front three-quarter.' },
  { id: 'base', area: '2 / 2 / 3 / 3', eyebrow: 'Data · Sample', meta: '#A-105', title: 'Headsets in use, by year',
    chart: [{ label: '21', value: 6 }, { label: '22', value: 11 }, { label: '23', value: 14 }, { label: '24', value: 17 }, { label: '25', value: 20 }] },
  { id: 'payload', area: '2 / 3 / 3 / 4', eyebrow: 'System', meta: '#A-106', title: 'Working payload: text, thumbnail, image, editable',
    code: ['panel.type     = "brief"', 'panel.sources  = 3', 'panel.media    = ["thumb", "image"]', 'panel.editable = true'] },
  { id: 'genres', area: '3 / 1 / 4 / 2', eyebrow: 'Data · Sample', meta: '#A-107', title: 'Top genres by hours',
    chart: [{ label: 'Soc', value: 34 }, { label: 'Sbx', value: 22 }, { label: 'Fit', value: 18 }, { label: 'Rhy', value: 12 }, { label: 'Oth', value: 8 }] },
  { id: 'bands', area: '3 / 2 / 4 / 3', eyebrow: 'Data · Sample', meta: '#A-108', title: 'Three bands used, three auth models',
    chart: [{ label: 'Low', value: 9 }, { label: 'Mid', value: 14 }, { label: 'High', value: 5 }], highlight: 1 },
  { id: 'sold', area: '3 / 3 / 4 / 4', eyebrow: 'Figure', meta: '#A-109',
    stat: { prefix: '≈', value: 20, suffix: 'm', label: 'Quest headsets sold', caption: 'Cumulatively by early 2025, as reported.' } },
  { id: 'build', area: '3 / 4 / 4 / 5', eyebrow: 'Runtime', meta: '#A-110',
    stat: { value: '27.15.0', label: 'Runtime build', caption: 'Uptime 72 h 16 · 10 panels' } },
];

function MediaBox({ label, play }) {
  const { IconButton } = DashDS;
  return (
    <div style={{ position: 'relative', flex: 1, minHeight: 60, display: 'grid', placeItems: 'center', background: 'var(--white-a04)', border: '1px solid var(--border-subtle)', backgroundImage: 'var(--bg-scanlines)' }}>
      <span style={{ font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wider)', color: 'var(--fg-3)', textTransform: 'uppercase' }}>{label}</span>
      {play && <div style={{ position: 'absolute', left: 8, bottom: 8 }}><IconButton icon="play" label="Play" size="sm" variant="outline" /></div>}
    </div>
  );
}

function DashPanel({ p, i, active, onActivate, onClose }) {
  const { Panel, BarChart, Stat } = DashDS;
  const body = { margin: 0, font: 'var(--type-body-sm)', color: 'var(--fg-2)', textWrap: 'pretty' };
  return (
    <Panel eyebrow={p.eyebrow} meta={p.meta} title={p.title} onClose={() => onClose(p.id)} active={active} delay={i * 55}
      onClick={() => onActivate(p.id)} bodyStyle={{ overflow: 'hidden' }} style={{ gridArea: p.area, minHeight: 0, overflow: 'hidden', cursor: 'default' }}
      footer={p.chart ? <span>SAMPLE DATA · ILLUSTRATIVE</span> : undefined}>
      {p.body && <p style={body}>{p.body}</p>}
      {p.media && <MediaBox label={p.media} play={p.play} />}
      {p.caption && <p style={{ ...body, fontSize: 'var(--fs-2xs)' }}>{p.caption}</p>}
      {p.chart && <div style={{ marginTop: 'auto' }}><BarChart data={p.chart} height={64} highlight={p.highlight ?? 'max'} /></div>}
      {p.code && (
        <pre style={{ margin: 0, padding: 8, background: 'var(--surface-sunken)', border: '1px solid var(--border-subtle)', font: 'var(--type-data)', fontSize: 'var(--fs-2xs)', color: 'var(--fg-2)', whiteSpace: 'pre-wrap' }}>
          {p.code.join('\n')}
        </pre>
      )}
      {p.stat && <div style={{ marginTop: 'auto' }}><Stat {...p.stat} size={typeof p.stat.value === 'number' ? 'lg' : 'sm'} /></div>}
    </Panel>
  );
}

function Dashboard({ panels, activeId, onActivate, onClose, camera }) {
  const { Panel, StatusDot } = DashDS;
  return (
    <div style={{ position: 'relative', height: '100%', display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0,1fr))', gridTemplateRows: 'repeat(3, minmax(0,1fr))', gap: 14 }}>
      {DASH_PANELS.filter((p) => panels.includes(p.id)).map((p, i) => (
        <DashPanel key={p.id} p={p} i={i} active={activeId === p.id} onActivate={onActivate} onClose={onClose} />
      ))}
      {camera && (
        <Panel eyebrow="Camera · Feed" meta="LIVE" interactive={false} style={{ position: 'absolute', left: '50%', top: '50%', width: 260, height: 180, transform: 'translate(-50%,-50%)', zIndex: 4, background: 'var(--ink-100)' }}
          actions={<StatusDot tone="live" size={4} />}>
          <MediaBox label="Camera feed" />
        </Panel>
      )}
    </div>
  );
}

Object.assign(window, { Dashboard, DASH_PANELS, MediaBox });
