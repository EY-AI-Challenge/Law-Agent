import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import Toolbar from './components/Toolbar'
import GraphView from './components/GraphView'
import ChatPanel from './components/ChatPanel'
import { fetchGraph, fetchStats } from './services/api'
import { MOCK_STATS } from './data/mockData'

export default function App() {
  const [activeTab, setActiveTab]         = useState('Código do Trabalho')
  const [nodes, setNodes]                 = useState([])
  const [edges, setEdges]                 = useState([])
  const [stats, setStats]                 = useState(MOCK_STATS)
  const [search, setSearch]               = useState('')
  const [filters, setFilters]             = useState({ CT: true, CC: true, DL: true })
  const [selectedNode, setSelectedNode]   = useState(null)
  const [pendingQuestion, setPending]     = useState(null)
  const [loading, setLoading]             = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [graph, s] = await Promise.all([fetchGraph(), fetchStats()])
        setNodes(graph.nodes)
        setEdges(graph.edges)
        setStats(s)
      } catch (err) {
        console.error('Failed to load graph:', err)
      }
      setLoading(false)
    }
    load()
  }, [])

  function toggleFilter(key) {
    setFilters(f => ({ ...f, [key]: !f[key] }))
  }

  function handleExploreNode(node) {
    setPending({
      text: `Explica as implicações legais de ${node.data.label} — ${node.data.title} e as suas conexões na rede legal portuguesa.`,
      context: node.data,
    })
    setSelectedNode(null)
  }

  function handleExport() {
    alert('Exportar grafo — funcionalidade disponível quando o backend estiver ligado.')
  }

  function handleReset() {
    setSearch('')
    setFilters({ CT: true, CC: true, DL: true })
    setSelectedNode(null)
  }

  return (
    <div className="flex flex-col h-screen">
      <Navbar activeTab={activeTab} onTabChange={setActiveTab} />

      <Toolbar
        search={search}
        onSearch={setSearch}
        filters={filters}
        onToggleFilter={toggleFilter}
        onExport={handleExport}
        onReset={handleReset}
      />

      <div className="flex flex-1 overflow-hidden">
        {loading ? (
          <div className="flex-1 flex items-center justify-center bg-[#12121A]">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 bg-ey-yellow rotate-45 rounded-sm pulse-dot" />
              <span className="text-ey-muted text-sm">A carregar rede legal...</span>
            </div>
          </div>
        ) : (
          <GraphView
            nodes={nodes}
            edges={edges}
            stats={stats}
            filters={filters}
            search={search}
            selectedNode={selectedNode}
            onSelectNode={setSelectedNode}
            onExploreNode={handleExploreNode}
          />
        )}

        <ChatPanel
          pendingQuestion={pendingQuestion}
          onPendingHandled={() => setPending(null)}
        />
      </div>
    </div>
  )
}
