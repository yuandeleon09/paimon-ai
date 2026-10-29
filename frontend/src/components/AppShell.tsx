import React from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

interface AppShellProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  projectId: string;
  onChangeProject: (proj: string) => void;
  model: string;
  vaultNotesCount: number;
  isConnected: boolean;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentTab,
  onSelectTab,
  projectId,
  onChangeProject,
  model,
  vaultNotesCount,
  isConnected,
  children,
}) => {
  const getTabTitle = () => {
    switch (currentTab) {
      case 'chat': return 'Chat & Task Workspace';
      case 'agents': return 'Multi-Agent Specialist Activity';
      case 'graph': return 'Interactive Knowledge Graph';
      case 'memory': return 'Obsidian Smart Memory Center';
      case 'automations': return 'Automations & Pipelines';
      case 'settings': return 'System Settings & Controls';
      default: return 'Antigravity AI';
    }
  };

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden', backgroundColor: 'var(--bg)' }}>
      {/* Navigation Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={onSelectTab}
        projectId={projectId}
        onChangeProject={onChangeProject}
        isConnected={isConnected}
      />

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        <Topbar
          title={getTabTitle()}
          model={model}
          vaultNotesCount={vaultNotesCount}
          isConnected={isConnected}
        />
        <main style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          {children}
        </main>
      </div>
    </div>
  );
};
