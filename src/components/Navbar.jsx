import { Search, User, Globe, ChevronDown } from 'lucide-react'

const NAV_LINKS = ['Insights', 'Serviços', 'Indústrias', 'Carreiras', 'Sobre nós']
const SUB_LINKS = ['Código do Trabalho', 'Código Civil', 'AI Assistant']

export default function Navbar({ activeTab, onTabChange }) {
  return (
    <div className="flex-shrink-0">
      {/* Top bar */}
      <div className="bg-ey-dark h-12 flex items-center px-5 gap-0 border-b border-ey-border">
        {/* Logo */}
        <div className="flex items-center gap-2 mr-7 flex-shrink-0">
          <div className="w-6 h-6 bg-ey-yellow rotate-45 rounded-sm" />
          <div className="leading-tight">
            <div className="text-white text-[13px] font-medium">Law Agent</div>
            <div className="text-ey-muted text-[10px]">Shape the future with confidence</div>
          </div>
        </div>

        {/* Nav links */}
        <div className="flex flex-1">
          {NAV_LINKS.map(link => (
            <button
              key={link}
              className="text-ey-muted text-[12px] px-3.5 h-12 hover:text-white transition-colors border-b-2 border-transparent"
            >
              {link}
            </button>
          ))}
        </div>

        {/* Right icons */}
        <div className="flex items-center gap-3 ml-auto">
          <Search className="w-4 h-4 text-ey-muted hover:text-white cursor-pointer transition-colors" />
          <User className="w-4 h-4 text-ey-muted hover:text-white cursor-pointer transition-colors" />
          <div className="flex items-center gap-1 text-ey-muted text-[11px] cursor-pointer hover:text-white transition-colors">
            <Globe className="w-3.5 h-3.5" />
            <span>Portugal</span>
            <ChevronDown className="w-3 h-3" />
          </div>
        </div>
      </div>

      {/* Sub nav */}
      <div className="bg-ey-panel h-9 flex items-center px-5 gap-1 border-b border-ey-border">
        {SUB_LINKS.map(link => (
          <button
            key={link}
            onClick={() => onTabChange(link)}
            className={`text-[12px] px-3 h-9 transition-colors border-b-2 ${
              activeTab === link
                ? 'text-ey-yellow border-ey-yellow'
                : 'text-ey-muted border-transparent hover:text-white'
            }`}
          >
            {link}
          </button>
        ))}

        {/* Live indicator */}
        <div className="ml-auto flex items-center gap-2 text-[11px] text-ey-muted">
          <div className="w-1.5 h-1.5 bg-ey-yellow rounded-full pulse-dot" />
          <span>Mock data — backend pending</span>
        </div>
      </div>
    </div>
  )
}
