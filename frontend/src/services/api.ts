import type {
  SystemStatus,
  Conversation,
  Message,
  ChatTaskResult,
  AgentRole,
  KnowledgeGraphData,
  MemoryItem,
  HealthReport,
  AutomationSummary
} from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errorDetail = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  // System Status
  async getStatus(): Promise<SystemStatus> {
    return fetchJson<SystemStatus>('/api/status');
  },

  // Conversations & Chat
  async listConversations(projectId: string = 'default'): Promise<{ conversations: Conversation[] }> {
    return fetchJson<{ conversations: Conversation[] }>(`/api/conversations?project_id=${projectId}`);
  },

  async createConversation(title: string, projectId: string = 'default'): Promise<{ conversation_id: string; title: string }> {
    return fetchJson('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({ title, project_id: projectId }),
    });
  },

  async getMessages(conversationId: string): Promise<{ messages: Message[] }> {
    return fetchJson<{ messages: Message[] }>(`/api/messages?conversation_id=${conversationId}`);
  },

  async sendChat(
    payload: {
      task: string;
      project_id: string;
      conversation_id: string;
      allow_revise?: boolean;
      collaborative?: boolean;
    },
    files?: File[]
  ): Promise<ChatTaskResult> {
    if (files && files.length > 0) {
      const formData = new FormData();
      formData.append('task', payload.task);
      formData.append('project_id', payload.project_id);
      formData.append('conversation_id', payload.conversation_id);
      if (payload.allow_revise !== undefined) {
        formData.append('allow_revise', String(payload.allow_revise));
      }
      if (payload.collaborative !== undefined) {
        formData.append('collaborative', String(payload.collaborative));
      }
      for (const f of files) {
        formData.append('files', f);
      }

      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        let errorDetail = `Request failed: ${res.status} ${res.statusText}`;
        try {
          const errJson = await res.json();
          if (errJson.detail) errorDetail = errJson.detail;
        } catch {
          // ignore
        }
        throw new Error(errorDetail);
      }

      return res.json();
    }

    return fetchJson<ChatTaskResult>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Agents & Collaboration
  async getAgents(): Promise<{
    roles: AgentRole[];
    recent_runs: any[];
    latest_team_idea: any;
  }> {
    return fetchJson('/api/agents');
  },

  // Knowledge Graph
  async getGraph(projectId?: string): Promise<KnowledgeGraphData> {
    const q = projectId ? `?project_id=${projectId}` : '';
    return fetchJson<KnowledgeGraphData>(`/api/graph${q}`);
  },

  // Memory Center
  async getMemory(): Promise<{
    approved: MemoryItem[];
    pending: MemoryItem[];
    conflicts: MemoryItem[];
    archived: MemoryItem[];
  }> {
    return fetchJson('/api/memory');
  },

  async approveMemory(lessonId: string, editedText?: string): Promise<{ success: boolean; lesson_id: string }> {
    return fetchJson('/api/memory/approve', {
      method: 'POST',
      body: JSON.stringify({ lesson_id: lessonId, edited_text: editedText }),
    });
  },

  async rejectMemory(lessonId: string, reason?: string): Promise<{ success: boolean; lesson_id: string }> {
    return fetchJson('/api/memory/reject', {
      method: 'POST',
      body: JSON.stringify({ lesson_id: lessonId, reason }),
    });
  },

  async archiveMemory(lessonId: string, reason?: string): Promise<{ success: boolean; lesson_id: string }> {
    return fetchJson('/api/memory/archive', {
      method: 'POST',
      body: JSON.stringify({ lesson_id: lessonId, reason }),
    });
  },

  async restoreMemory(lessonId: string): Promise<{ success: boolean; lesson_id: string }> {
    return fetchJson('/api/memory/restore', {
      method: 'POST',
      body: JSON.stringify({ lesson_id: lessonId }),
    });
  },

  // Memory Health
  async getMemoryHealth(): Promise<HealthReport> {
    return fetchJson<HealthReport>('/api/memory/health');
  },

  async applyHealthFix(findingId: string): Promise<{ success: boolean; message: string; backup_id?: string }> {
    return fetchJson('/api/memory/health/fix', {
      method: 'POST',
      body: JSON.stringify({ finding_id: findingId }),
    });
  },

  async restoreHealthBackup(backupId: string): Promise<{ success: boolean; backup_id: string }> {
    return fetchJson('/api/memory/health/restore', {
      method: 'POST',
      body: JSON.stringify({ backup_id: backupId }),
    });
  },

  // Automations
  async getAutomations(): Promise<AutomationSummary> {
    return fetchJson<AutomationSummary>('/api/automations');
  },

  // Settings
  async getSettings(): Promise<any> {
    return fetchJson('/api/settings');
  },
};
