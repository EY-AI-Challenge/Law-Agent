import { useCallback, useMemo } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap,
  useNodesState, useEdgesState,
  addEdge, BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'
import LawNode from './LawNode'
import NodePopup from './NodePopup'
import StatsBar from './StatsBar'
import GraphLegend from './GraphLegend'

const nodeTypes = { lawNode: LawNode }

const EDGE_STYLE = { stroke: '#FFFFFF18', strokeWidth: 1 }
const EDGE_STYLE_HIGHLIGHTED = { stroke: '#FFE60055', strokeWidth: 2 }

export default function GraphView({
  nodes: rawNodes, edges: rawEdges, stats,
  filters, search,
  selectedNode, onSelectNode,
  onExploreNode,
}) {
  const visibleNodes = useMemo(() => {
    return rawNodes
      .filter(n => {
        const code = n.data.code
        if (!filters[code]) return false
        if (search) {
          const s = search.toLowerCase()
          return (
            n.data.label.toLowerCase().includes(s) ||
            n.data.title.toLowerCase().includes(s) ||
            n.data.cluster.toLowerCase().includes(s)
          )
        }
        return true
      })
      .map(n => ({
        ...n,
        selected: selectedNode?.id === n.id,
        style: {
          opacity: search && !n.data.label.toLowerCase().includes(search.toLowerCase()) &&
                   !n.data.title.toLowerCase().includes(search.toLowerCase()) &&
                   !n.data.cluster.toLowerCase().includes(search.toLowerCase()) ? 0.3 : 1
        }
      }))
  }, [rawNodes, filters, search, selectedNode])

  const visibleIds = useMemo(() => new Set(visibleNodes.map(n => n.id)), [visibleNodes])

  const visibleEdges = useMemo(() => {
    return rawEdges
      .filter(e => visibleIds.has(e.source) && visibleIds.has(e.target))
      .map(e => {
        const isHighlighted = selectedNode &&
          (e.source === selectedNode.id || e.target === selectedNode.id)
        return {
          ...e,
          style: isHighlighted ? EDGE_STYLE_HIGHLIGHTED : EDGE_STYLE,
          animated: isHighlighted,
        }
      })
  }, [rawEdges, visibleIds, selectedNode])

  const onNodeClick = useCallback((_, node) => {
    onSelectNode(selectedNode?.id === node.id ? null : node)
  }, [selectedNode, onSelectNode])

  const onPaneClick = useCallback(() => onSelectNode(null), [onSelectNode])

  return (
    <div className="flex-1 relative bg-[#12121A]">
      <ReactFlow
        nodes={visibleNodes}
        edges={visibleEdges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        defaultEdgeOptions={{ style: EDGE_STYLE }}
        minZoom={0.3}
        maxZoom={3}
      >
        <Background variant={BackgroundVariant.Dots} color="#2A2A3A" gap={24} size={1} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={n => {
            if (n.data?.code === 'CT') return '#FFE600'
            if (n.data?.code === 'CC') return '#4A90D9'
            return '#555'
          }}
          maskColor="#12121Aaa"
        />
      </ReactFlow>

      <StatsBar stats={stats} />
      <GraphLegend />

      {selectedNode && (
        <NodePopup
          node={selectedNode}
          onClose={() => onSelectNode(null)}
          onExplore={onExploreNode}
        />
      )}
    </div>
  )
}
