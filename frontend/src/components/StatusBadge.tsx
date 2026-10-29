import React from 'react';
import { CheckCircle2, Clock, AlertTriangle, AlertCircle, ShieldAlert } from 'lucide-react';

interface StatusBadgeProps {
  status: string;
  variant?: 'success' | 'warning' | 'error' | 'neutral' | 'primary';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, variant }) => {
  let color = 'var(--muted)';
  let bg = 'var(--surface-hover)';
  let Icon = Clock;

  const s = status.toLowerCase();
  if (variant === 'success' || s === 'completed' || s === 'approved' || s === 'passed' || s === 'low') {
    color = 'var(--success)';
    bg = '#142924';
    Icon = CheckCircle2;
  } else if (variant === 'warning' || s === 'pending' || s === 'medium' || s === 'working') {
    color = 'var(--warning)';
    bg = '#2C2513';
    Icon = AlertTriangle;
  } else if (variant === 'error' || s === 'failed' || s === 'error' || s === 'high' || s === 'rejected') {
    color = 'var(--error)';
    bg = '#2E191B';
    Icon = s === 'high' ? ShieldAlert : AlertCircle;
  } else if (variant === 'primary' || s === 'active') {
    color = 'var(--primary)';
    bg = '#162338';
    Icon = Clock;
  }

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '3px 8px',
        borderRadius: 'var(--radius-sm)',
        fontSize: '12px',
        fontWeight: 500,
        color: color,
        backgroundColor: bg,
        border: `1px solid ${color}`,
        whiteSpace: 'nowrap',
      }}
    >
      <Icon size={13} />
      <span>{status}</span>
    </span>
  );
};
