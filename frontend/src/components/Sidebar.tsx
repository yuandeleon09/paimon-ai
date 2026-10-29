import React from 'react';
import {
  MessageSquare,
  Users,
  Network,
  BookOpen,
  Zap,
  Settings,
  FolderGit2,
  Server
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  projectId: string;
  onChangeProject: (proj: string) => void;
  isConnected: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  projectId,
  isConnected,
}) => {
  const navItems = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'agents', label: 'Agents', icon: Users },
    { id: 'graph', label: 'Knowledge Graph', icon: Network },
    { id: 'memory', label: 'Memory', icon: BookOpen },
    { id: 'automations', label: 'Automations', icon: Zap },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside
      style={{
        width: '240px',
        minWidth: '240px',
        backgroundColor: 'var(--sidebar)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        userSelect: 'none',
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: '20px 16px 16px 16px',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--primary)',
              color: '#0D1420',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '15px',
            }}
          >
            A
          </div>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.3px' }}>
              Antigravity AI
            </div>
            <div style={{ fontSize: '11px', color: 'var(--muted)' }}>
              Gemini + Obsidian Team
            </div>
          </div>
        </div>

        {/* Project Context */}
        <div
          style={{
            marginTop: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 10px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            fontSize: '12px',
          }}
        >
          <FolderGit2 size={14} color="var(--muted)" />
          <span style={{ color: 'var(--muted)' }}>Scope:</span>
          <span style={{ fontWeight: 600, color: 'var(--text)' }}>{projectId}</span>
        </div>
      </div>

      {/* Main Navigation */}
      <nav style={{ flex: 1, padding: '16px 10px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '9px 12px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: isActive ? 'var(--surface)' : 'transparent',
                border: `1px solid ${isActive ? 'var(--border)' : 'transparent'}`,
                color: isActive ? 'var(--primary)' : 'var(--muted)',
                fontWeight: isActive ? 600 : 500,
                textAlign: 'left',
              }}
            >
              <Icon size={18} color={isActive ? 'var(--primary)' : 'var(--muted)'} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer Connection Status */}
      <div
        style={{
          padding: '16px',
          borderTop: '1px solid var(--border)',
          backgroundColor: 'var(--sidebar)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
          <Server size={14} color={isConnected ? 'var(--success)' : 'var(--error)'} />
          <span style={{ color: isConnected ? 'var(--text)' : 'var(--muted)' }}>
            {isConnected ? 'Backend Live' : 'Backend Offline'}
          </span>
        </div>
        <div
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: isConnected ? 'var(--success)' : 'var(--error)',
          }}
        />
      </div>
    </aside>
  );
};
