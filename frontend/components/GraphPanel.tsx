"use client";

import { useEffect, useRef, useState } from "react";

interface GraphNode {
  id: string;
  label: string;
  type: string;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const NODE_COLORS: Record<string, string> = {
  Company: "#818cf8",
  Country: "#34d399",
  Jurisdiction: "#fb923c",
  Address: "#f472b6",
  Node: "#94a3b8",
};

export default function GraphPanel({
  lei,
  onNodeClick,
}: {
  lei: string;
  onNodeClick?: (lei: string) => void;
}) {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const [ForceGraph, setForceGraph] = useState<any>(null);

  useEffect(() => {
    import("react-force-graph-2d").then((mod) => {
      setForceGraph(() => mod.default);
    });
  }, []);

  useEffect(() => {
    const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    setLoading(true);
    fetch(`${api}/entities/${lei}/graph`)
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(() => setData({ nodes: [], edges: [] }))
      .finally(() => setLoading(false));
  }, [lei]);

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500 text-sm">
        Loading graph...
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="h-32 flex items-center justify-center text-gray-500 text-sm">
        No graph data available for this entity.
      </div>
    );
  }

  if (!ForceGraph) {
    return (
      <div className="h-32 flex items-center justify-center text-gray-500 text-sm">
        Loading visualiser...
      </div>
    );
  }

  const graphData = {
    nodes: data.nodes.map((n) => ({ ...n, name: n.label })),
    links: data.edges.map((e) => ({
      source: e.source,
      target: e.target,
      label: e.type,
    })),
  };

  return (
    <div ref={containerRef} className="rounded-lg overflow-hidden bg-gray-950 border border-gray-700">
      <ForceGraph
        graphData={graphData}
        width={containerRef.current?.offsetWidth || 600}
        height={300}
        backgroundColor="#030712"
        nodeLabel="name"
        nodeColor={(n: any) => NODE_COLORS[n.type] || NODE_COLORS.Node}
        nodeRelSize={5}
        linkLabel="label"
        linkColor={() => "#374151"}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        linkWidth={1.5}
        onNodeClick={(node: any) => {
          if (node.type === "Company" && node.id && onNodeClick) {
            onNodeClick(node.id);
          }
        }}
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const label = node.name as string;
          const fontSize = 10 / globalScale;
          ctx.font = `${fontSize}px Inter, sans-serif`;
          ctx.fillStyle = NODE_COLORS[node.type] || NODE_COLORS.Node;
          ctx.beginPath();
          ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI);
          ctx.fill();
          ctx.fillStyle = "#e5e7eb";
          ctx.textAlign = "center";
          ctx.fillText(label.length > 20 ? label.slice(0, 18) + "…" : label, node.x, node.y + 10);
        }}
      />
      <div className="flex gap-3 px-3 py-2 border-t border-gray-800 flex-wrap">
        {Object.entries(NODE_COLORS).slice(0, 4).map(([type, color]) => (
          <span key={type} className="flex items-center gap-1 text-xs text-gray-400">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
            {type}
          </span>
        ))}
      </div>
    </div>
  );
}
