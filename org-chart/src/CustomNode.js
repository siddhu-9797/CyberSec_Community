import React from "react";
import { Handle, Position } from "reactflow";
import "./App.css"; // Ensure CSS is imported

export default function CustomNode({ data }) {
  return (
    <div className="node-card">
      {/* Incoming edge connection point */}
      <Handle type="target" position={Position.Top} />

      {/* Avatar */}
      <img src={data.avatar} className="avatar" alt={data.name} />

      {/* Text content container */}
      <div className="node-text">
        <div className="name">{data.name}</div>
        <div className="title">{data.title}</div>
      </div>

      {/* Outgoing edge connection point */}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
