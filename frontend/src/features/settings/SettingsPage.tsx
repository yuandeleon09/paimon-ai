import React, { useState, useEffect } from 'react';
import { Shield, Cpu, HardDrive, Sliders } from 'lucide-react';
import { api } from '../../services/api';
import { StatusBadge } from '../../components/StatusBadge';

interface SettingsPageProps {
  projectId: string;
  onChangeProject: (proj: string) => void;
  isConnected: boolean;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  projectId,
  onChangeProject,
  isConnected,
}) => {
  const [settings, setSettings] = useState<any>({
    gemini_model: 'gemini-3.5-flash-lite',
    has_api_key: true,
    vault_connected: true,
    vault_name: 'Obsidian-Brain',
    max_calls: 8,
    max_revisions: 1,
    retention_days: 14,
    theme: 'dark',
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      setSettings(data);
    } catch {
      // offline fallback
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '800px', height: '100%', overflowY: 'auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text)', marginBottom: '6px' }}>
          System Configuration & Settings
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--muted)' }}>
          Local system configuration, active models, vault status, and quota safety parameters.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Backend & Model Settings */}
        <div
          style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Cpu size={18} color="var(--primary)" />
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)' }}>
              AI Model & Quota Protection
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>Server Status</div>
              <StatusBadge
                status={isConnected ? 'Connected' : 'Offline'}
                variant={isConnected ? 'success' : 'error'}
              />
            </div>

            <div>
              <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>Active Model</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>
                {settings.gemini_model} <span style={{ color: 'var(--primary)', fontSize: '12px' }}>(Free-Tier)</span>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>API Key Status</div>
              <StatusBadge
                status={settings.has_api_key ? 'Configured (.env)' : 'Missing'}
                variant={settings.has_api_key ? 'success' : 'error'}
              />
            </div>

            <div>
              <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>Call Budget Cap</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>
                Max {settings.max_calls} calls / task
              </div>
            </div>

            <div>
              <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>Max Revisions</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>
                {settings.max_revisions} revision round
              </div>
            </div>
          </div>
        </div>

        {/* Vault & Storage Status */}
        <div
          style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <HardDrive size={18} color="var(--success)" />
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)' }}>
              Obsidian Vault & Memory Center
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>Vault Directory</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>
                {settings.vault_name}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>Storage Status</div>
              <StatusBadge
                status={settings.vault_connected ? 'Connected' : 'Unavailable'}
                variant={settings.vault_connected ? 'success' : 'error'}
              />
            </div>

            <div>
              <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>Diagnostic Retention</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>
                {settings.retention_days} Days (state.sqlite)
              </div>
            </div>
          </div>
        </div>

        {/* Project Scope Context */}
        <div
          style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Sliders size={18} color="var(--warning)" />
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)' }}>
              Project Scope & Isolation
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '360px' }}>
            <label style={{ fontSize: '12px', color: 'var(--muted)', fontWeight: 600 }}>Active Project ID</label>
            <input
              type="text"
              value={projectId}
              onChange={(e) => onChangeProject(e.target.value)}
              style={{
                fontSize: '13px',
                padding: '8px 12px',
                backgroundColor: 'var(--bg)',
              }}
            />
            <span style={{ fontSize: '11px', color: 'var(--muted)' }}>
              Memory retrieval is strictly scoped to this project identifier.
            </span>
          </div>
        </div>

        {/* Security Invariant Notice */}
        <div
          style={{
            padding: '16px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text)', fontWeight: 600, marginBottom: '6px', fontSize: '13px' }}>
            <Shield size={16} color="var(--primary)" />
            <span>Zero Secrets in Client UI</span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.5 }}>
            API secrets (`GEMINI_API_KEY`) remain stored exclusively in your local `.env` file on Windows and are never transmitted to or displayed inside the browser interface.
          </p>
        </div>
      </div>
    </div>
  );
};
