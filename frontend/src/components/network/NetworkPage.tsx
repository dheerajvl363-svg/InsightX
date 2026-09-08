import React, { useState, useEffect, useRef } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Hash,
  AtSign,
  Sliders,
  Play,
  Pause,
} from 'lucide-react';
import { Card, Badge, Button, Skeleton, ErrorBanner } from '../common';
import { useNetwork } from '../../hooks/useNetwork';
import { Network } from 'vis-network';

export const NetworkPage: React.FC = () => {
  const [physicsEnabled, setPhysicsEnabled] = useState(true);
  const [entityType, setEntityType] = useState<'all' | 'hashtag' | 'mention'>('all');
  const [minWeight, setMinWeight] = useState<number>(2);

  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);

  // useNetwork hook
  const { data, loading, error, refetch } = useNetwork();

  // Initialize network when data is ready
  useEffect(() => {
    if (!containerRef.current || !data) return;

    let filteredNodes = data.nodes;
    let filteredEdges = data.edges;

    if (entityType === 'hashtag') {
      filteredNodes = filteredNodes.filter((n) => n.node_type === 'hashtag');
    } else if (entityType === 'mention') {
      filteredNodes = filteredNodes.filter((n) => n.node_type === 'author');
    }

    filteredEdges = filteredEdges.filter((e) => e.weight >= minWeight);

    // Keep only edges that connect nodes still present
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    filteredEdges = filteredEdges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));

    const visNodes = filteredNodes.map((n) => ({
      id: n.id,
      label: n.label,
      value: n.degree || 1, // for sizing
      group: n.node_type,
      color: n.node_type === 'hashtag' ? '#00d2ff' : '#8b5cf6',
      font: { color: '#e2e8f0', size: 12 },
    }));

    const visEdges = filteredEdges.map((e) => ({
      from: e.source,
      to: e.target,
      value: e.weight,
      color: { color: 'rgba(255,255,255,0.1)', highlight: '#00d2ff' },
      smooth: { enabled: true, type: 'continuous', roundness: 0.5 },
    }));

    const networkData = {
      nodes: visNodes,
      edges: visEdges,
    };

    const options = {
      nodes: {
        shape: 'dot',
        scaling: { min: 10, max: 40 },
        borderWidth: 2,
        borderWidthSelected: 4,
      },
      edges: {
        scaling: { min: 1, max: 10 },
      },
      physics: {
        enabled: physicsEnabled,
        barnesHut: { gravitationalConstant: -2000, centralGravity: 0.1, springLength: 150 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        zoomView: true,
      },
    };

    if (!networkRef.current) {
      networkRef.current = new Network(containerRef.current, networkData, options);
    } else {
      networkRef.current.setData(networkData);
      networkRef.current.setOptions(options);
    }

    const net = networkRef.current;
    
    // Cleanup old event listeners
    net.off('selectNode');
    net.off('deselectNode');

    net.on('selectNode', (params) => {
      const nodeId = params.nodes[0];
      const nodeInfo = data.nodes.find((n) => n.id === nodeId);
      if (nodeInfo) setSelectedNode(nodeInfo);
    });

    net.on('deselectNode', () => {
      setSelectedNode(null);
    });

    return () => {
      // Don't destroy on every re-render, only on unmount
    };
  }, [data, entityType, minWeight, physicsEnabled]);

  useEffect(() => {
    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, []);

  const handleZoomIn = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale();
      networkRef.current.moveTo({ scale: scale * 1.5 });
    }
  };

  const handleZoomOut = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale();
      networkRef.current.moveTo({ scale: scale / 1.5 });
    }
  };

  const handleFit = () => {
    if (networkRef.current) {
      networkRef.current.fit({ animation: true });
    }
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '1rem',
          marginBottom: '1.75rem',
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
              marginBottom: '0.35rem',
            }}
          >
            Entity Co-occurrence Network Graph
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.925rem' }}>
            Interactive relational topology connecting hashtags and user mentions across social streams.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Badge variant="cyan" size="md">
            Endpoint: GET /api/v1/analytics/network
          </Badge>
        </div>
      </div>

      {/* Graph Control Bar Card */}
      <Card style={{ marginBottom: '1.5rem', padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          {/* Entity Type Toggle Chips */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              Entity Filter:
            </span>
            <div style={{ display: 'flex', gap: '0.25rem', backgroundColor: 'var(--bg-tertiary)', padding: '0.2rem', borderRadius: 'var(--radius-sm)' }}>
              {[
                { id: 'all', label: 'All Entities' },
                { id: 'hashtag', label: '#Hashtags', icon: <Hash size={12} /> },
                { id: 'mention', label: '@Mentions', icon: <AtSign size={12} /> },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setEntityType(tab.id as any)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                    background: entityType === tab.id ? 'var(--bg-surface)' : 'transparent',
                    color: entityType === tab.id ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                    border: 'none',
                    borderRadius: 'var(--radius-xs)',
                    padding: '0.3rem 0.65rem',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Min Weight Control */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Sliders size={16} color="var(--text-muted)" />
            <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
              Min Weight: <strong style={{ color: 'var(--accent-cyan)' }}>{minWeight}</strong>
            </span>
            <input
              type="range"
              min="1"
              max="10"
              value={minWeight}
              onChange={(e) => setMinWeight(Number(e.target.value))}
              style={{ accentColor: 'var(--accent-cyan)', cursor: 'pointer', width: '100px' }}
            />
          </div>

          {/* Action Tools */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Button
              size="sm"
              variant={physicsEnabled ? 'secondary' : 'outline'}
              icon={physicsEnabled ? <Pause size={14} /> : <Play size={14} />}
              onClick={() => setPhysicsEnabled(!physicsEnabled)}
            >
              {physicsEnabled ? 'Pause Physics' : 'Resume'}
            </Button>
            <Button size="sm" variant="secondary" icon={<ZoomIn size={14} />} title="Zoom In" onClick={handleZoomIn} />
            <Button size="sm" variant="secondary" icon={<ZoomOut size={14} />} title="Zoom Out" onClick={handleZoomOut} />
            <Button size="sm" variant="secondary" icon={<Maximize2 size={14} />} title="Fit View" onClick={handleFit} />
          </div>
        </div>
      </Card>

      {/* Error Banners if any endpoint fails */}
      {error && (
        <ErrorBanner
          title="Network Graph Analytics Failed"
          message={error}
          onRetry={refetch}
        />
      )}

      {/* Main Graph Viewport Card */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 300px',
          gap: '1.5rem',
          minHeight: '560px',
        }}
        className="network-grid"
      >
        {/* Graph Canvas Container */}
        <Card style={{ padding: 0, overflow: 'hidden', position: 'relative', minHeight: '520px' }}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <Skeleton width="100%" height="100%" />
            </div>
          ) : (
            <div
              style={{
                width: '100%',
                height: '100%',
                minHeight: '520px',
                backgroundColor: '#070b14',
                backgroundImage: 'radial-gradient(rgba(0, 210, 255, 0.1) 1px, transparent 1px)',
                backgroundSize: '24px 24px',
                position: 'relative',
              }}
            >
              <div ref={containerRef} style={{ width: '100%', height: '100%', minHeight: '520px', outline: 'none' }} />
              
              {/* Floating Canvas Legend */}
              <div
                style={{
                  position: 'absolute',
                  top: '1rem',
                  left: '1rem',
                  backgroundColor: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.6rem 0.85rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.4rem',
                  backdropFilter: 'blur(8px)',
                  fontSize: '0.78rem',
                  pointerEvents: 'none',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-cyan)' }} />
                  <span style={{ color: 'var(--text-secondary)' }}>Hashtags (Nodes)</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-purple)' }} />
                  <span style={{ color: 'var(--text-secondary)' }}>User Mentions (Nodes)</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                  <span style={{ width: '12px', height: '2px', backgroundColor: 'var(--border-muted)' }} />
                  <span style={{ color: 'var(--text-secondary)' }}>Co-occurrence Weight (Edges)</span>
                </div>
              </div>
              
              {/* Network Stats Legend */}
              <div
                style={{
                  position: 'absolute',
                  bottom: '1rem',
                  left: '1rem',
                  backgroundColor: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.6rem 0.85rem',
                  display: 'flex',
                  gap: '1rem',
                  backdropFilter: 'blur(8px)',
                  fontSize: '0.78rem',
                  pointerEvents: 'none',
                }}
              >
                <span style={{ color: 'var(--text-secondary)' }}>Nodes: <strong style={{ color: 'var(--text-primary)' }}>{data?.total_nodes ?? 0}</strong></span>
                <span style={{ color: 'var(--text-secondary)' }}>Edges: <strong style={{ color: 'var(--text-primary)' }}>{data?.total_edges ?? 0}</strong></span>
              </div>
            </div>
          )}
        </Card>

        {/* Selected Entity Inspector Panel */}
        <Card title="Entity Inspector" subtitle="Selected Node Telemetry">
          {loading ? (
             <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', paddingTop: '0.25rem' }}>
               <Skeleton width="100%" height="60px" borderRadius="var(--radius-md)" />
               <Skeleton width="100%" height="20px" />
               <Skeleton width="100%" height="20px" />
             </div>
          ) : selectedNode ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', paddingTop: '0.25rem' }}>
              <div
                style={{
                  padding: '0.85rem',
                  backgroundColor: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                  Node Detail
                </div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                  {selectedNode.label}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Type</span>
                  <Badge variant={selectedNode.node_type === 'hashtag' ? 'cyan' : 'primary'} size="sm">
                    {selectedNode.node_type === 'hashtag' ? 'Hashtag' : 'Author'}
                  </Badge>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Degree Centrality</span>
                  <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{selectedNode.degree} Connections</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Influence Score</span>
                  <span style={{ color: 'var(--sentiment-pos)', fontWeight: 600 }}>{selectedNode.influence_score.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Node ID</span>
                  <span style={{ color: 'var(--accent-purple)', fontSize: '0.75rem' }}>{selectedNode.id}</span>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '2rem', fontSize: '0.85rem' }}>
              Select a node on the graph to inspect its telemetry.
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
