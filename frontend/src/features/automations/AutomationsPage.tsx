import React, { useState, useEffect } from 'react';
import { Zap, ExternalLink, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { api } from '../../services/api';
import type { AutomationSummary } from '../../services/types';
import { EmptyState } from '../../components/EmptyState';

export const AutomationsPage: React.FC = () => {
  const [automations, setAutomations] = useState<AutomationSummary>({
    connected: false,
    service: 'n8n',
    url: null,
    message: 'No automations connected',
    workflows: [],
  });

  useEffect(() => {
    loadAutomations();
  }, []);

  const loadAutomations = async () => {
    try {
      const data = await api.getAutomations();
      setAutomations(data);
    } catch {
      // offline fallback
    }
  };

  return (
    <div style={{ padding: '24px', height: '100%', overflowY: 'auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text)', marginBottom: '6px' }}>
          External Automations & Workflows (n8n)
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--muted)' }}>
          Status overview of external integrations and webhooks. Does not run unverified automations.
        </p>
      </div>

      {automations.connected ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div
            style={{
              padding: '16px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: '#142924',
              border: '1px solid var(--success)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <CheckCircle2 size={20} color="var(--success)" />
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: '14px' }}>
                  Connected to {automations.service}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--muted)' }}>{automations.url}</div>
              </div>
            </div>
            {automations.url && (
              <a
                href={automations.url}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  color: 'var(--primary)',
                  fontSize: '13px',
                  fontWeight: 600,
                  textDecoration: 'none',
                }}
              >
                <span>Open {automations.service}</span>
                <ExternalLink size={14} />
              </a>
            )}
          </div>
        </div>
      ) : (
        <div style={{ maxWidth: '600px' }}>
          <EmptyState
            icon={Zap}
            title="No Automations Connected"
            description="n8n automation webhooks and scheduled external pipelines are not configured in this local environment. Workflows will appear here once an n8n webhook URL is configured in settings."
          />

          <div
            style={{
              marginTop: '24px',
              padding: '16px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text)', fontWeight: 600, marginBottom: '8px', fontSize: '13px' }}>
              <ShieldCheck size={16} color="var(--primary)" />
              <span>Integration Security Policy</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.5 }}>
              In accordance with project safety guidelines, agent actions are strictly isolated locally. Outside webhooks, email transmissions, and automated external tasks require explicit operator consent before execution.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
