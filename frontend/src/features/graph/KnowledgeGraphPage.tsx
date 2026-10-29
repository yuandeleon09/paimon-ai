import React, { useState, useEffect, useRef } from 'react';
import cytoscape, { type Core } from 'cytoscape';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Search,
  Filter,
  Eye,
  EyeOff,
  Network
} from 'lucide-react';
import { api } from '../../services/api';
import type { KnowledgeGraphData } from '../../services/types';
import { GraphInspector } from './GraphInspector';
import { EmptyState } from '../../components/EmptyState';

interface KnowledgeGraphPageProps {
  projectId: string;
  onOpenMemory?: (noteId: string) => void;
}

export const KnowledgeGraphPage: React.FC<KnowledgeGraphPageProps> = ({
  projectId,
  onOpenMemory,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const [graphData, setGraphData] = useState<KnowledgeGraphData>({ nodes: [], edges: [], total_nodes: 0, total_edges: 0 });
  const [selectedElement, setSelectedElement] = useState<{ isNode: boolean; data: any } | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showLabels, setShowLabels] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Type filters
  const [activeFilters, setActiveFilters] = useState<Record<string, boolean>>({
    Agent: true,
    Memory: true,
    Task: true,
    Idea: true,
    Project: true,
  });

  useEffect(() => {
    loadGraphData();
  }, [projectId]);

  const loadGraphData = async () => {
    setIsLoading(true);
    try {
      const data = await api.getGraph(projectId);
      setGraphData(data);
    } catch {
      // Fallback: minimal demo node structure if offline
      setGraphData({
        nodes: [
          { data: { id: 'proj-default', label: 'Project: default', kind: 'Project', type: 'project' } },
          { data: { id: 'agent-planner', label: 'Planner', kind: 'Agent', type: 'agent' } },
          { data: { id: 'agent-developer', label: 'Developer', kind: 'Agent', type: 'agent' } },
        ],
        edges: [
          { data: { id: 'e1', source: 'agent-planner', target: 'proj-default', label: 'belongs_to_project', type: 'belongs_to_project' } },
        ],
        total_nodes: 3,
        total_edges: 1,
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Initialize or update Cytoscape instance
  useEffect(() => {
    if (!containerRef.current || isLoading) return;

    // Filter nodes by activeFilters and search query
    const filteredNodes = graphData.nodes.filter((n) => {
      const kindMatch = activeFilters[n.data.kind] !== false;
      const searchMatch = !searchQuery || n.data.label.toLowerCase().includes(searchQuery.toLowerCase());
      return kindMatch && searchMatch;
    });

    const activeNodeIds = new Set(filteredNodes.map((n) => n.data.id));

    // Filter edges connected to active nodes
    const filteredEdges = graphData.edges.filter(
      (e) => activeNodeIds.has(e.data.source) && activeNodeIds.has(e.data.target)
    );

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...filteredNodes, ...filteredEdges],
      style: [
        // Base Node Style (Zero Gradients, Solid Surface)
        {
          selector: 'node',
          style: {
            'background-color': '#172333',
            'border-width': 2,
            'border-color': '#304054',
            'label': showLabels ? 'data(label)' : '',
            'color': '#F1F5F9',
            'font-family': 'system-ui, sans-serif',
            'font-size': 11,
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'width': 34,
            'height': 34,
            'text-wrap': 'ellipsis',
            'text-max-width': '120px',
            'transition-property': 'background-color, border-color, border-width',
            'transition-duration': 0.15,
          },
        },
        // Agent Node: Muted Blue
        {
          selector: 'node[kind = "Agent"]',
          style: {
            'background-color': '#6EA8F7',
            'border-color': '#5A96E5',
            'shape': 'ellipse',
            'color': '#6EA8F7',
          },
        },
        // Memory Node: Teal
        {
          selector: 'node[kind = "Memory"]',
          style: {
            'background-color': '#48BFA1',
            'border-color': '#3CA88D',
            'shape': 'round-rectangle',
            'color': '#48BFA1',
          },
        },
        // Task Node: Amber
        {
          selector: 'node[kind = "Task"]',
          style: {
            'background-color': '#E6B85C',
            'border-color': '#CFA348',
            'shape': 'rectangle',
            'color': '#E6B85C',
          },
        },
        // Idea Node: Muted Violet
        {
          selector: 'node[kind = "Idea"]',
          style: {
            'background-color': '#AA96DD',
            'border-color': '#937FC4',
            'shape': 'diamond',
            'color': '#AA96DD',
            'width': 38,
            'height': 38,
          },
        },
        // Project Node: Gray
        {
          selector: 'node[kind = "Project"]',
          style: {
            'background-color': '#9CAFC5',
            'border-color': '#8295AB',
            'shape': 'round-rectangle',
            'color': '#9CAFC5',
            'width': 44,
            'height': 30,
          },
        },
        // Selected Node Highlight
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#FFFFFF',
          },
        },
        // Base Edge Style: Solid thin line, low opacity
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#304054',
            'target-arrow-color': '#304054',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'opacity': 0.75,
            'label': showLabels ? 'data(label)' : '',
            'font-size': 9,
            'color': '#A8B5C6',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
          },
        },
        {
          selector: 'edge:selected',
          style: {
            'width': 2.5,
            'line-color': '#6EA8F7',
            'target-arrow-color': '#6EA8F7',
            'opacity': 1,
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        nodeOverlap: 20,
        idealEdgeLength: 80,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        padding: 40,
      },
    });

    // Tap node handler
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      setSelectedElement({ isNode: true, data: node.data() });
    });

    // Tap edge handler
    cy.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      setSelectedElement({ isNode: false, data: edge.data() });
    });

    // Tap background handler
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedElement(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [graphData, activeFilters, searchQuery, showLabels, isLoading]);

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit(undefined, 40);
  const handleResetLayout = () => {
    cyRef.current?.layout({ name: 'cose', animate: false }).run();
  };

  const toggleFilter = (kind: string) => {
    setActiveFilters((prev) => ({ ...prev, [kind]: !prev[kind] }));
  };

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%', overflow: 'hidden' }}>
      {/* Canvas and Controls Region */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
        {/* Top Filter and Search Bar */}
        <div
          style={{
            padding: '12px 20px',
            backgroundColor: 'var(--surface)',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            zIndex: 10,
          }}
        >
          {/* Search Input */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '240px' }}>
            <Search size={16} color="var(--muted)" />
            <input
              type="text"
              placeholder="Search nodes by title..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                flex: 1,
                fontSize: '12px',
                padding: '6px 10px',
                backgroundColor: 'var(--bg)',
              }}
            />
          </div>

          {/* Type Filter Pills */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '12px', color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Filter size={13} />
              <span>Types:</span>
            </span>

            {[
              { kind: 'Agent', color: '#6EA8F7' },
              { kind: 'Memory', color: '#48BFA1' },
              { kind: 'Task', color: '#E6B85C' },
              { kind: 'Idea', color: '#AA96DD' },
              { kind: 'Project', color: '#9CAFC5' },
            ].map((f) => {
              const active = activeFilters[f.kind];
              return (
                <button
                  key={f.kind}
                  onClick={() => toggleFilter(f.kind)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 8px',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '11px',
                    fontWeight: 600,
                    backgroundColor: active ? 'var(--surface-hover)' : 'transparent',
                    border: `1px solid ${active ? f.color : 'var(--border)'}`,
                    color: active ? f.color : 'var(--muted)',
                  }}
                >
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: f.color }} />
                  <span>{f.kind}</span>
                </button>
              );
            })}
          </div>

          {/* Canvas View Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              onClick={() => setShowLabels(!showLabels)}
              title="Toggle Labels"
              style={{
                padding: '6px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface-hover)',
                color: showLabels ? 'var(--primary)' : 'var(--muted)',
              }}
            >
              {showLabels ? <Eye size={15} /> : <EyeOff size={15} />}
            </button>
            <button
              onClick={handleZoomIn}
              title="Zoom In"
              style={{
                padding: '6px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface-hover)',
                color: 'var(--text)',
              }}
            >
              <ZoomIn size={15} />
            </button>
            <button
              onClick={handleZoomOut}
              title="Zoom Out"
              style={{
                padding: '6px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface-hover)',
                color: 'var(--text)',
              }}
            >
              <ZoomOut size={15} />
            </button>
            <button
              onClick={handleFit}
              title="Fit to Screen"
              style={{
                padding: '6px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface-hover)',
                color: 'var(--text)',
              }}
            >
              <Maximize2 size={15} />
            </button>
            <button
              onClick={handleResetLayout}
              title="Reset Layout"
              style={{
                padding: '6px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface-hover)',
                color: 'var(--text)',
              }}
            >
              <RotateCcw size={15} />
            </button>
          </div>
        </div>

        {/* Cytoscape 2D Canvas */}
        <div
          ref={containerRef}
          style={{
            flex: 1,
            width: '100%',
            height: '100%',
            backgroundColor: 'var(--bg)',
          }}
        />

        {/* Empty State Overlay */}
        {graphData.nodes.length === 0 && !isLoading && (
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }}>
            <EmptyState
              icon={Network}
              title="No Relationships Recorded Yet"
              description="Execute tasks in Chat to record real connections between agents, tasks, team ideas, and approved Obsidian memories."
            />
          </div>
        )}
      </div>

      {/* Right Details Inspector */}
      {selectedElement && (
        <GraphInspector
          selectedElement={selectedElement}
          onClose={() => setSelectedElement(null)}
          onOpenMemory={onOpenMemory}
        />
      )}
    </div>
  );
};
