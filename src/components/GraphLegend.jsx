const LEGEND = [
  { color: '#FFE600', label: 'Código do Trabalho' },
  { color: '#4A90D9', label: 'Código Civil' },
  { color: '#777',   label: 'Decreto-Lei' },
  { color: '#E05A5A', label: 'Nó central (hub)', ring: true },
]

export default function GraphLegend() {
  return (
    <div className="absolute bottom-3 left-3 z-10 bg-ey-card border border-ey-border rounded-xl p-3 flex flex-col gap-2">
      {LEGEND.map(l => (
        <div key={l.label} className="flex items-center gap-2 text-[11px] text-ey-muted">
          <div
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{
              background: l.color,
              outline: l.ring ? `2px solid ${l.color}` : 'none',
              outlineOffset: l.ring ? '2px' : '0',
            }}
          />
          {l.label}
        </div>
      ))}
    </div>
  )
}
