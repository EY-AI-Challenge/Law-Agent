import { X, ExternalLink } from 'lucide-react'

const CODE_ACCENT = { CT: '#FFE600', CC: '#4A90D9', DL: '#777' }

export default function NodePopup({ node, onClose, onExplore }) {
  if (!node) return null
  const { data } = node
  const accent = CODE_ACCENT[data.code] || '#777'

  return (
    <div className="absolute top-4 left-4 z-10 w-64 bg-ey-card border rounded-xl p-4 msg-anim"
      style={{ borderColor: accent }}>

      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-medium" style={{ color: accent }}>
              {data.label}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded"
              style={{ background: accent + '22', color: accent }}>
              {data.code}
            </span>
          </div>
          <div className="text-white text-[12px] font-medium mt-0.5">{data.title}</div>
        </div>
        <button onClick={onClose} className="text-ey-muted hover:text-white transition-colors ml-2 mt-0.5">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Description */}
      <p className="text-ey-muted text-[11px] leading-relaxed mb-3">{data.desc}</p>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        {[
          { label: 'Referências', value: data.refs },
          { label: 'Cluster', value: data.cluster },
          { label: 'Centralidade', value: data.centrality },
        ].map(s => (
          <div key={s.label} className="bg-ey-panel rounded-lg p-2 text-center">
            <div className="text-[11px] font-medium" style={{ color: accent }}>{s.value}</div>
            <div className="text-[9px] text-ey-muted mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Action */}
      <button
        onClick={() => onExplore(node)}
        className="w-full flex items-center justify-center gap-1.5 text-[11px] font-medium py-2 rounded-lg transition-all hover:opacity-90"
        style={{ background: accent, color: data.code === 'CT' ? '#1A1A00' : '#fff' }}
      >
        <ExternalLink className="w-3.5 h-3.5" />
        Explorar no assistente
      </button>
    </div>
  )
}
