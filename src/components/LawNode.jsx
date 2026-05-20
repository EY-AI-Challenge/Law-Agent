import { Handle, Position } from 'reactflow'

const CODE_STYLES = {
  CT: { bg: '#FFE600', text: '#1A1A00', border: '#C8A800', badge: '#7A6400', badgeBg: '#FFF5B3' },
  CC: { bg: '#4A90D9', text: '#fff',    border: '#2A6AAD', badge: '#fff',    badgeBg: '#1A3A5C' },
  DL: { bg: '#555566', text: '#fff',    border: '#333344', badge: '#ccc',    badgeBg: '#2A2A3A' },
}

export default function LawNode({ data, selected }) {
  const style = CODE_STYLES[data.code] || CODE_STYLES.DL
  const size = data.isHub ? 80 : data.refs > 50 ? 70 : data.refs > 30 ? 62 : 54

  return (
    <div
      className="flex flex-col items-center justify-center rounded-full cursor-pointer transition-all"
      style={{
        width: size, height: size,
        background: style.bg,
        border: selected ? `3px solid #fff` : `2px solid ${style.border}`,
        boxShadow: selected ? `0 0 0 3px ${style.bg}44` : 'none',
      }}
    >
      <Handle type="target" position={Position.Top}    style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />

      <span
        className="font-medium text-center leading-tight"
        style={{
          color: style.text,
          fontSize: size > 70 ? 9 : 8,
          maxWidth: size - 10,
          wordBreak: 'break-word',
          textAlign: 'center',
          padding: '0 4px',
        }}
      >
        {data.label}
      </span>

      <span
        className="text-[7px] font-medium px-1 rounded mt-0.5"
        style={{ background: style.badgeBg, color: style.badge }}
      >
        {data.code}
      </span>
    </div>
  )
}
