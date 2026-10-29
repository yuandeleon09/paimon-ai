import React from 'react';
import { Cpu, HardDrive, CheckCircle2 } from 'lucide-react';

interface TopbarProps {
  title: string;
  model: string;
  vaultNotesCount?: number;
  isConnected: boolean;
}

export const Topbar: React.FC<TopbarProps> = ({
  title,
  model,
  vaultNotesCount = 0,
  isConnected,
}) => {
  return (
    <header
      style={{
        height: '56px',
        borderBottom: '1px solid var(--border)',
        backgroundColor: 'var(--bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        flexShrink: 0,
      }}
    >
      <h1 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text)' }}>
        {title}
      </h1>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Model Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            fontSize: '12px',
            color: 'var(--text)',
          }}
        >
          <Cpu size={14} color="var(--primary)" />
          <span>{model || 'gemini-3.5-flash-lite'}</span>
          <span style={{ color: 'var(--muted)', fontSize: '11px' }}>(Free-Tier)</span>
        </div>

        {/* Vault Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            fontSize: '12px',
            color: 'var(--text)',
          }}
        >
          <HardDrive size={14} color="var(--success)" />
          <span>Obsidian Memory:</span>
          <span style={{ fontWeight: 600 }}>{vaultNotesCount} notes</span>
        </div>

        {/* Connection status */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: isConnected ? '#142924' : '#2E191B',
            border: `1px solid ${isConnected ? 'var(--success)' : 'var(--error)'}`,
            fontSize: '12px',
            color: isConnected ? 'var(--success)' : 'var(--error)',
            fontWeight: 500,
          }}
        >
          <CheckCircle2 size={13} />
          <span>{isConnected ? 'API Ready' : 'API Offline'}</span>
        </div>
      </div>
    </header>
  );
};
