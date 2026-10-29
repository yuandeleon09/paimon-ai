import React from 'react';
import { X, ExternalLink, Network } from 'lucide-react';
import { StatusBadge } from '../../components/StatusBadge';

interface GraphInspectorProps {
  selectedElement: {
    isNode: boolean;
    data: any;
  } | null;
  onClose: () => void;
  onOpenMemory?: (noteId: string) => void;
}

export const GraphInspector: React.FC<GraphInspectorProps> = ({
  selectedElement,
  onClose,
  onOpenMemory,
}) => {
  if (!selectedElement) return null;

  const { isNode, data } = selectedElement;

  return (
    <div
      style={{
        width: '320px',
        minWidth: '320px',
        backgroundColor: 'var(--surface)',
        borderLeft: '1px solid var(--border)',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: '20px',
        overflowY: 'auto',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Network size={18} color="var(--primary)" />
          <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)' }}>
            {isNode ? 'Node Details' : 'Relationship Details'}
          </h3>
        </div>
        <button onClick={onClose} style={{ color: 'var(--muted)', padding: '4px' }}>
          <X size={18} />
        </button>
      </div>

      {isNode ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '4px' }}>
              Title
            </div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text)' }}>
              {data.label}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontSize: '12px',
                fontWeight: 600,
                padding: '3px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--surface-hover)',
                border: '1px solid var(--border)',
                color: 'var(--text)',
              }}
            >
              Kind: {data.kind || data.type}
            </span>
            {data.status && <StatusBadge status={data.status} />}
          </div>

          {data.description && (
            <div>
              <div style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '4px' }}>
                Description / Excerpt
              </div>
              <div
                style={{
                  fontSize: '13px',
                  color: 'var(--muted)',
                  lineHeight: 1.5,
                  padding: '10px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--surface-hover)',
                  border: '1px solid var(--border)',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {data.description}
              </div>
            </div>
          )}

          {data.note_id && onOpenMemory && (
            <button
              onClick={() => onOpenMemory(data.note_id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--primary)',
                color: '#0D1420',
                fontWeight: 600,
                fontSize: '13px',
                marginTop: '10px',
              }}
            >
              <ExternalLink size={16} />
              <span>Inspect in Memory Center</span>
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '4px' }}>
              Relationship
            </div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--primary)' }}>
              <code>{data.label || data.type}</code>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: 'var(--text)' }}>
            <div>
              <span style={{ color: 'var(--muted)' }}>Source: </span>
              <strong>{data.source}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--muted)' }}>Target: </span>
              <strong>{data.target}</strong>
            </div>
          </div>

          <p style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.5 }}>
            Verified deterministic link recorded between knowledge entities.
          </p>
        </div>
      )}
    </div>
  );
};
