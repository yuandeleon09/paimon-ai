import React, { useState, useEffect } from 'react';
import {
  Users,
  Compass,
  Search,
  Code2,
  CheckCircle,
  FileCheck,
  BrainCircuit,
  HardDrive,
  Lightbulb,
  AlertTriangle,
  History
} from 'lucide-react';
import { api } from '../../services/api';
import type { AgentRole, TeamIdea } from '../../services/types';
import { StatusBadge } from '../../components/StatusBadge';
import { EmptyState } from '../../components/EmptyState';

export const AgentsPage: React.FC = () => {
  const [roles, setRoles] = useState<AgentRole[]>([]);
  const [recentRuns, setRecentRuns] = useState<any[]>([]);
  const [selectedRun, setSelectedRun] = useState<any | null>(null);

  useEffect(() => {
    loadAgentData();
  }, []);

  const loadAgentData = async () => {
    try {
      const data = await api.getAgents();
      setRoles(data.roles);
      setRecentRuns(data.recent_runs || []);
      if (data.recent_runs && data.recent_runs.length > 0) {
        setSelectedRun(data.recent_runs[0]);
      }
    } catch {
      // Offline fallback defaults for the 7 logical roles
      setRoles([
        { role: 'planner', title: 'Planner', description: 'Interprets goals and breaks tasks down into structured execution steps', status: 'Idle' },
        { role: 'researcher', title: 'Researcher', description: 'Gathers relevant context, files, and background information', status: 'Idle' },
        { role: 'developer', title: 'Developer', description: 'Produces requested implementations and verified code artifacts', status: 'Idle' },
        { role: 'tester', title: 'Tester', description: 'Formulates verification suites and reports truthful test outcomes', status: 'Idle' },
        { role: 'reviewer', title: 'Reviewer', description: 'Evaluates completeness, correctness, and adherence to requirements', status: 'Idle' },
        { role: 'learning_agent', title: 'Learning Agent', description: 'Assesses durable value and extracts atomic verified lessons', status: 'Idle' },
        { role: 'memory_manager', title: 'Memory Manager', description: 'Retrieves, filters, audits, and organizes approved vault knowledge', status: 'Idle' },
      ]);
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'planner': return Compass;
      case 'researcher': return Search;
      case 'developer': return Code2;
      case 'tester': return CheckCircle;
      case 'reviewer': return FileCheck;
      case 'learning_agent': return BrainCircuit;
      case 'memory_manager': return HardDrive;
      default: return Users;
    }
  };

  let teamIdea: TeamIdea | null = null;
  if (selectedRun && selectedRun.team_idea_json) {
    try {
      teamIdea = typeof selectedRun.team_idea_json === 'string'
        ? JSON.parse(selectedRun.team_idea_json)
        : selectedRun.team_idea_json;
    } catch {
      teamIdea = null;
    }
  }

  return (
    <div style={{ padding: '24px', height: '100%', overflowY: 'auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text)', marginBottom: '6px' }}>
          Logical Specialist Roles (Seven Agents)
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--muted)' }}>
          Single Gemini free-tier provider routed to specialized roles. Configured logical agents formulate independent proposals and synthesize collaborative Team Ideas.
        </p>
      </div>

      {/* 7 Specialist Roles Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '14px',
          marginBottom: '32px',
        }}
      >
        {roles.map((r) => {
          const Icon = getRoleIcon(r.role);
          return (
            <div
              key={r.role}
              style={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div
                      style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: 'var(--surface-hover)',
                        border: '1px solid var(--border)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--primary)',
                      }}
                    >
                      <Icon size={18} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: '14px' }}>{r.title}</div>
                      <div style={{ fontSize: '11px', color: 'var(--muted)' }}>{r.role}</div>
                    </div>
                  </div>
                  <StatusBadge status={r.status} />
                </div>
                <p style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.5, marginBottom: '12px' }}>
                  {r.description}
                </p>
              </div>

              {r.last_task && (
                <div
                  style={{
                    fontSize: '11px',
                    color: 'var(--text)',
                    backgroundColor: 'var(--surface-hover)',
                    padding: '6px 8px',
                    borderRadius: 'var(--radius-sm)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  Last: {r.last_task}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Task Collaboration & Pipeline Section */}
      <div style={{ borderTop: '1px solid var(--border)', paddingTop: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <History size={18} color="var(--primary)" />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text)' }}>
              Recent Task Collaboration Details
            </h3>
          </div>
          {recentRuns.length > 0 && (
            <select
              value={selectedRun?.run_id || ''}
              onChange={(e) => {
                const found = recentRuns.find((r) => r.run_id === e.target.value);
                if (found) setSelectedRun(found);
              }}
              style={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                color: 'var(--text)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '12px',
                padding: '6px 10px',
              }}
            >
              {recentRuns.map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {r.task.slice(0, 35)}... ({r.status})
                </option>
              ))}
            </select>
          )}
        </div>

        {selectedRun ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '16px' }}>
            {/* Task Overview & Pipeline Steps */}
            <div
              style={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '18px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ fontSize: '12px', color: 'var(--muted)' }}>Run ID: {selectedRun.run_id}</span>
                <StatusBadge status={selectedRun.status} />
              </div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text)', marginBottom: '14px' }}>
                Task: {selectedRun.task}
              </div>

              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', marginBottom: '10px' }}>
                Pipeline Contributions
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {selectedRun.steps && selectedRun.steps.map((step: any, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'var(--surface-hover)',
                      fontSize: '13px',
                    }}
                  >
                    <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{step.agent}</span>
                    <StatusBadge status={step.status} />
                  </div>
                ))}
              </div>
            </div>

            {/* Synthesized Team Idea Card */}
            <div
              style={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '18px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)', marginBottom: '12px' }}>
                <Lightbulb size={18} />
                <span style={{ fontSize: '14px', fontWeight: 700 }}>Synthesized Team Idea</span>
              </div>

              {teamIdea ? (
                <div>
                  <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)', marginBottom: '8px' }}>
                    {teamIdea.title}
                  </h4>
                  <p style={{ fontSize: '13px', color: 'var(--muted)', lineHeight: 1.6, marginBottom: '14px' }}>
                    {teamIdea.synthesis}
                  </p>

                  {teamIdea.conflicts_detected && teamIdea.conflicts_detected.length > 0 && (
                    <div
                      style={{
                        padding: '10px 12px',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: '#2E191B',
                        border: '1px solid var(--error)',
                        fontSize: '12px',
                        color: 'var(--error)',
                        marginBottom: '12px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, marginBottom: '4px' }}>
                        <AlertTriangle size={14} />
                        <span>Preserved Conflicts / Alternatives</span>
                      </div>
                      <div>{teamIdea.conflicts_detected.join('; ')}</div>
                    </div>
                  )}

                  {teamIdea.relationships && teamIdea.relationships.length > 0 && (
                    <div>
                      <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '6px' }}>
                        Specialist Proposal Relationships
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {teamIdea.relationships.map((rel, i) => (
                          <div
                            key={i}
                            style={{
                              fontSize: '12px',
                              color: 'var(--text)',
                              padding: '6px 8px',
                              borderRadius: 'var(--radius-sm)',
                              backgroundColor: 'var(--surface-hover)',
                            }}
                          >
                            <strong>{rel.from_role}</strong> <code>{rel.rel_type}</code> <strong>{rel.to_role}</strong>: {rel.reason}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ color: 'var(--muted)', fontSize: '13px', padding: '24px 0', textAlign: 'center' }}>
                  No Team Idea generated for this task run.
                </div>
              )}
            </div>
          </div>
        ) : (
          <EmptyState
            icon={History}
            title="No Task Collaboration History"
            description="Run tasks in Chat with 'Collaborative Team Room' enabled to view specialist idea correlation and synthesis."
          />
        )}
      </div>
    </div>
  );
};
