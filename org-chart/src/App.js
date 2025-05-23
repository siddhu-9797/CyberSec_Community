import React, { useEffect } from "react";
import ReactFlow, {
  // Controls, // Keep controls commented out if you don't want them visible
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  // MarkerType, // Keep commented if not used
} from "reactflow";
import "reactflow/dist/style.css";
import "./App.css";

import CustomNode from "./CustomNode";

const nodeTypes = { custom: CustomNode };
// const seed = Math.random().toString(36).substr(2, 9); // Keep if used by CustomNode

// --- Initial Nodes (Keep as is) ---
const initialNodes = [
  // ... your nodes ...
  {
    id: "1",
    type: "custom",
    position: { x: 350, y: 25 },
    data: {
      name: "Sarah Chen",
      title: "CEO",
      avatar: "https://randomuser.me/api/portraits/women/44.jpg",
    },
  },
  {
    id: "7",
    type: "custom",
    position: { x: 0, y: 200 },
    data: {
      name: "You",
      title: "CISO",
      avatar: `https://api.dicebear.com/9.x/pixel-art/svg`,
    },
    style: {
      backgroundColor: "#e3f2fd",
      border: "3px solid #2196F3",
      borderRadius: "8px",
      boxShadow: "0 4px 12px rgba(33, 150, 243, 0.4)",
    },
  },
  {
    id: "3",
    type: "custom",
    position: { x: 233, y: 200 },
    data: {
      name: "Maria Garcia",
      title: "Head of Public Relations",
      avatar: "https://randomuser.me/api/portraits/women/68.jpg",
    },
  },
  {
    id: "6",
    type: "custom",
    position: { x: 466, y: 200 },
    data: {
      name: "Laura Mitchell",
      title: "Chief Operating Officer",
      avatar: "https://randomuser.me/api/portraits/women/50.jpg",
    },
  },
  {
    id: "2",
    type: "custom",
    position: { x: 700, y: 200 },
    data: {
      name: "David Rodriguez",
      title: "General Counsel",
      avatar: "https://randomuser.me/api/portraits/men/32.jpg",
    },
  },
  {
    id: "4",
    type: "custom",
    position: { x: 0, y: 350 },
    data: {
      name: "James Bennett",
      title: "Head of IT Security",
      avatar: "https://randomuser.me/api/portraits/men/76.jpg",
    },
  },
  {
    id: "5",
    type: "custom",
    position: { x: 0, y: 500 },
    data: {
      name: "Ethan Kim",
      title: "Senior Security Analyst",
      avatar: "https://randomuser.me/api/portraits/men/64.jpg",
    },
  },
];

// --- Initial Edges (Keep as is) ---
const initialEdges = [
  // ... your edges ...
  { id: "e1-2", source: "1", target: "2" },
  { id: "e1-3", source: "1", target: "3" },
  { id: "e1-6", source: "1", target: "6" },
  { id: "e1-7", source: "1", target: "7" },
  { id: "e7-4", source: "7", target: "4" },
  { id: "e4-5", source: "4", target: "5" },
];

// --- Default Edge Options (Keep as is) ---
const defaultEdgeOptions = {
  // ... options ...
  style: { strokeWidth: 1.5, stroke: "#b1b1b7", strokeDasharray: "5,5" },
};

// --- Pro Options (Keep as is) ---
const proOptions = { hideAttribution: true };

function FlowComponent() {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges); // Removed setEdges if not used directly
  const { fitView } = useReactFlow(); // Removed setViewport if simplifying

  useEffect(() => {
    // Simple fitView on mount
    fitView({ padding: 0.2, duration: 0 });
    // Removed the setTimeout and setViewport forcing the zoom
  }, [fitView]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      defaultEdgeOptions={defaultEdgeOptions}
      proOptions={proOptions}
      // --- ENABLE PANNING ---
      panOnDrag={true} // Allow dragging to pan
      panOnScroll={true} // Optional: Allow scroll gesture to pan (test usability)
      // --- REMOVE/RELAX ZOOM LOCK ---
      zoomOnScroll={true} // Optional: Allow scroll to zoom
      zoomOnPinch={true} // Optional: Allow pinch to zoom (good for mobile)
      zoomOnDoubleClick={true} // Optional: Allow double click to zoom
      minZoom={0.2} // Example: Allow zooming out
      maxZoom={1.5} // Example: Allow zooming in slightly
      // --- Keep other interaction settings as desired ---
      // nodesDraggable={false} // Keep commented (draggable) or uncomment if needed
      // elementsSelectable={false} // Keep commented (selectable) or uncomment if needed
    >
      {/* <Controls showInteractive={false} /> */}
      <Background variant="dots" gap={15} size={0.6} color="#e0e0e0" />
    </ReactFlow>
  );
}

// --- App component remains the same ---
function App() {
  return (
    <div className="org-chart-container">
      <ReactFlowProvider>
        <FlowComponent />
      </ReactFlowProvider>
    </div>
  );
}

export default App;
