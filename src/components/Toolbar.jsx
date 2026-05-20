import { Search, Download, Maximize2, RotateCcw } from 'lucide-react'

const FILTERS = [
  { key: 'CT', label: 'Cód. Trabalho', color: '#FFE600' },
  { key: 'CC', label: 'Código Civil',  color: '#4A90D9' },
  { key: 'DL', label: 'Decretos-Lei',  color: '#777777' },
]

export default function Toolbar({ search, onSearch, filters, onToggleFilter, onExport, onReset }) {
  return (
    <div className="flex-shrink-0 bg-[#1E1E2A] h-11 flex items-center px-4 gap-2 border-b border-ey-border">

      {/* Search */}
      <div className="flex items-center bg-ey-panel border border-ey-border rounded-md px-2.5 gap-2 h-7 w-56">
        <Search className="w-3.5 h-3.5 text-ey-muted flex-shrink-0" />
        <input
          value={search}
          onChange={e => onSearch(e.target.value)}
          placeholder="Pesquisar artigo ou lei..."
          className="bg-transparent text-white text-[11px] outline-none placeholder-[#555] w-full"
        />
      </div>

      <div className="w-px h-5 bg-ey-border mx-1" />

      {/* Type filters */}
      {FILTERS.map(f => (
        <button
          key={f.key}
          onClick={() => onToggleFilter(f.key)}
          className={`flex items-center gap-1.5 text-[11px] px-2.5 h-7 rounded-md border transition-all ${
            filters[f.key]
              ? 'border-current'
              : 'border-ey-border text-[#444] opacity-50'
          }`}
          style={{ color: filters[f.key] ? f.color : undefined }}
        >
          <span
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: filters[f.key] ? f.color : '#444' }}
          />
          {f.label}
        </button>
      ))}

      <div className="w-px h-5 bg-ey-border mx-1" />

      {/* Cluster label */}
      <span className="text-[11px] text-ey-muted">Cluster:</span>

      {/* Action buttons */}
      <div className="ml-auto flex items-center gap-1.5">
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 text-[11px] text-ey-muted px-2.5 h-7 rounded-md border border-ey-border hover:border-ey-muted hover:text-white transition-all"
        >
          <RotateCcw className="w-3.5 h-3.5" /> Reset
        </button>
        <button
          onClick={onExport}
          className="flex items-center gap-1.5 text-[11px] text-ey-muted px-2.5 h-7 rounded-md border border-ey-border hover:border-ey-muted hover:text-white transition-all"
        >
          <Download className="w-3.5 h-3.5" /> Exportar
        </button>
        <button
          className="flex items-center gap-1.5 text-[11px] text-ey-yellow px-2.5 h-7 rounded-md border border-ey-yellow hover:bg-ey-yellow hover:text-ey-dark transition-all"
        >
          <Maximize2 className="w-3.5 h-3.5" /> Expandir
        </button>
      </div>
    </div>
  )
}
