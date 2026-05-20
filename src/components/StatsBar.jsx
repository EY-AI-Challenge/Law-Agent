export default function StatsBar({ stats }) {
  const items = [
    { value: stats.totalDocs.toLocaleString(), label: 'documentos legais' },
    { value: stats.totalRefs.toLocaleString(), label: 'referências' },
    { value: stats.clusters,                   label: 'clusters' },
    { value: stats.centralLaw,                 label: 'lei mais central' },
  ]

  return (
    <div className="absolute top-3 left-3 flex gap-2 z-10">
      {items.map(item => (
        <div key={item.label}
          className="flex items-center gap-2 bg-ey-card border border-ey-border rounded-full px-3 py-1.5">
          <span className="text-ey-yellow text-[13px] font-medium">{item.value}</span>
          <span className="text-ey-muted text-[11px]">{item.label}</span>
        </div>
      ))}
    </div>
  )
}
