import React, { useState, useEffect } from 'react';
import './styles/global.css';
import { AppShell } from './components/AppShell';
import { ChatPage } from './features/chat/ChatPage';
import { AgentsPage } from './features/agents/AgentsPage';
import { KnowledgeGraphPage } from './features/graph/KnowledgeGraphPage';
import { MemoryPage } from './features/memory/MemoryPage';
import { AutomationsPage } from './features/automations/AutomationsPage';
import { SettingsPage } from './features/settings/SettingsPage';
import { api } from './services/api';
import type { SystemStatus } from './services/types';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('chat');
  const [projectId, setProjectId] = useState<string>('default');
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(true);
  const [selectedNoteId, setSelectedNoteId] = useState<string | undefined>(undefined);

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const checkStatus = async () => {
    try {
      const s = await api.getStatus();
      setStatus(s);
      setIsConnected(true);
    } catch {
      setIsConnected(false);
    }
  };

  const handleOpenMemory = (noteId: string) => {
    setSelectedNoteId(noteId);
    setCurrentTab('memory');
  };

  const totalVaultNotes = status
    ? (status.vault_stats.approved_notes + status.vault_stats.pending_notes)
    : 0;

  return (
    <AppShell
      currentTab={currentTab}
      onSelectTab={(tab) => {
        setCurrentTab(tab);
        if (tab !== 'memory') setSelectedNoteId(undefined);
      }}
      projectId={projectId}
      onChangeProject={setProjectId}
      model={status?.gemini_model || 'gemini-3.5-flash-lite'}
      vaultNotesCount={totalVaultNotes}
      isConnected={isConnected}
    >
      {currentTab === 'chat' && (
        <ChatPage
          projectId={projectId}
          onOpenMemory={handleOpenMemory}
          isConnected={isConnected}
        />
      )}
      {currentTab === 'agents' && <AgentsPage />}
      {currentTab === 'graph' && (
        <KnowledgeGraphPage
          projectId={projectId}
          onOpenMemory={handleOpenMemory}
        />
      )}
      {currentTab === 'memory' && <MemoryPage initialNoteId={selectedNoteId} />}
      {currentTab === 'automations' && <AutomationsPage />}
      {currentTab === 'settings' && (
        <SettingsPage
          projectId={projectId}
          onChangeProject={setProjectId}
          isConnected={isConnected}
        />
      )}
    </AppShell>
  );
};

export default App;
