'use client'

import 'reactflow/dist/style.css'
import ReactFlow, { Background, MarkerType } from 'reactflow'

const nodes = [
  {
    id: 'capture',
    position: { x: 0, y: 60 },
    data: { label: 'Omnichannel Input' },
    style: { borderRadius: 12, border: '1px solid #d5def5', background: '#fff', padding: 8, width: 170 },
  },
  {
    id: 'router',
    position: { x: 230, y: 20 },
    data: { label: 'Intent Router' },
    style: { borderRadius: 12, border: '1px solid #d5def5', background: '#fff', padding: 8, width: 160 },
  },
  {
    id: 'rag',
    position: { x: 230, y: 120 },
    data: { label: 'Knowledge RAG' },
    style: { borderRadius: 12, border: '1px solid #d5def5', background: '#fff', padding: 8, width: 160 },
  },
  {
    id: 'crm',
    position: { x: 460, y: 60 },
    data: { label: 'CRM + Automation' },
    style: { borderRadius: 12, border: '1px solid #d5def5', background: '#fff', padding: 8, width: 170 },
  },
]

const edges = [
  { id: 'e1-2', source: 'capture', target: 'router', markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e1-3', source: 'capture', target: 'rag', markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e2-4', source: 'router', target: 'crm', markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e3-4', source: 'rag', target: 'crm', markerEnd: { type: MarkerType.ArrowClosed } },
]

export default function WorkflowFlow() {
  return (
    <div className="card mt-6 h-[260px] overflow-hidden">
      <ReactFlow edges={edges} fitView nodes={nodes} nodesDraggable={false} panOnDrag={false} zoomOnScroll={false}>
        <Background color="#edf2ff" gap={18} />
      </ReactFlow>
    </div>
  )
}
