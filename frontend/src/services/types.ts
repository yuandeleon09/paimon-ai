export interface SystemStatus {
  status: string;
  gemini_model: string;
  api_key_configured: boolean;
  vault_connected: boolean;
  vault_stats: {
    approved_notes: number;
    pending_notes: number;
    conflicts: number;
    archived_notes: number;
    total_vault_kb: number;
  };
  max_calls: number;
  timestamp: string;
}

export interface Conversation {
  id: string;
  title: string;
  project_id: string;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  agent_name?: string;
  created_at: string;
}

export interface StepRecord {
  agent: string;
  status: string;
  result?: string;
  duration?: number;
}

export interface TeamIdea {
  title: string;
  synthesis: string;
  tradeoffs?: string[];
  conflicts_detected?: string[];
  relationships?: Array<{
    from_role: string;
    to_role: string;
    rel_type: string;
    reason: string;
  }>;
  contributor_ids?: string[];
}

export interface AttachmentMeta {
  filename: string;
  extension: string;
  size_bytes: number;
  category: string;
  warnings?: string[];
}

export interface TaskLogicalBudget {
  used_known_attempts: number;
  limit: number;
  remaining: number;
  tokens?: {
    input_tokens_known: number;
    output_tokens_known: number;
    total_tokens_known: number;
  };
}

export interface ProviderQuotaInfo {
  status: string;
  source: string;
}

export interface ChatTaskResult {
  run_id: string;
  task_id?: string;
  status: string;
  verdict: string;
  result: string;
  steps: StepRecord[];
  team_idea?: TeamIdea;
  memory_decision?: {
    score: number;
    should_store: boolean;
    rationale: string;
  };
  saved_candidate_ids?: string[];
  run_metadata?: Record<string, any>;
  attachments?: AttachmentMeta[];
  attachment_warnings?: string[];
  logical_budget?: TaskLogicalBudget;
  provider_quota?: ProviderQuotaInfo;
  can_resume_now?: boolean;
  pause_reason?: string;
  partial_result_available?: boolean;
  is_deduplicated?: boolean;
}

export interface AgentRole {
  role: string;
  title: string;
  description: string;
  status: 'Idle' | 'Active' | 'Completed' | 'Error';
  last_task?: string;
}

export interface GraphNode {
  data: {
    id: string;
    label: string;
    kind: 'Agent' | 'Memory' | 'Task' | 'Idea' | 'Project';
    type: string;
    description?: string;
    note_id?: string;
    run_id?: string;
    status?: string;
  };
}

export interface GraphEdge {
  data: {
    id: string;
    source: string;
    target: string;
    label: string;
    type: string;
  };
}

export interface KnowledgeGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
}

export interface MemoryItem {
  id: string;
  filename: string;
  content: string;
  preview?: string;
  bytes: number;
}

export interface HealthFinding {
  finding_id: string;
  finding_type: string;
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
  affected_note_ids: string[];
  reason: string;
  proposed_diff: string;
  suggested_action: string;
  status: string;
}

export interface HealthReport {
  timestamp: string;
  approved_notes_count: number;
  pending_notes_count: number;
  conflicts_count: number;
  archived_notes_count: number;
  total_approved_bytes: number;
  findings: HealthFinding[];
}

export interface AutomationSummary {
  connected: boolean;
  service: string;
  url: string | null;
  message: string;
  workflows: Array<{
    id: string;
    name: string;
    active: boolean;
    last_run?: string;
  }>;
}
