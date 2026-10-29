import React, { useState, useEffect } from 'react';
import {
  Archive,
  RotateCcw,
  Stethoscope,
  Search,
  Check,
  X,
  Edit3,
  FileText
} from 'lucide-react';
import { api } from '../../services/api';
import type { MemoryItem, HealthReport, HealthFinding } from '../../services/types';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { EmptyState } from '../../components/EmptyState';

interface MemoryPageProps {
  initialNoteId?: string;
}

export const MemoryPage: React.FC<MemoryPageProps> = ({ initialNoteId }) => {
  const [activeTab, setActiveTab] = useState<'approved' | 'pending' | 'health' | 'archived'>('approved');
  const [memoryData, setMemoryData] = useState<{
    approved: MemoryItem[];
    pending: MemoryItem[];
    conflicts: MemoryItem[];
    archived: MemoryItem[];
  }>({ approved: [], pending: [], conflicts: [], archived: [] });

  const [selectedNote, setSelectedNote] = useState<MemoryItem | null>(null);
  const [editingContent, setEditingContent] = useState<string>('');
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Health check state
  const [healthReport, setHealthReport] = useState<HealthReport | null>(null);
  const [isScanning, setIsScanning] = useState<boolean>(false);

  // Confirmation dialog state
  const [dialogConfig, setDialogConfig] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    confirmText?: string;
    isDestructive?: boolean;
    action: () => Promise<void>;
  }>({
    isOpen: false,
    title: '',
    message: '',
    action: async () => {},
  });

  useEffect(() => {
    loadMemory();
  }, []);

  useEffect(() => {
    if (initialNoteId && memoryData.approved.length > 0) {
      const match = memoryData.approved.find((n) => n.id === initialNoteId);
      if (match) setSelectedNote(match);
    }
  }, [initialNoteId, memoryData]);

  const loadMemory = async () => {
    try {
      const data = await api.getMemory();
      setMemoryData(data);
      if (!selectedNote && data.approved.length > 0) {
        setSelectedNote(data.approved[0]);
      }
    } catch {
      // ignore
    }
  };

  const handleRunHealthCheck = async () => {
    setIsScanning(true);
    try {
      const report = await api.getMemoryHealth();
      setHealthReport(report);
      loadMemory();
    } catch {
      // ignore
    } finally {
      setIsScanning(false);
    }
  };

  const handleApprove = (item: MemoryItem) => {
    setDialogConfig({
      isOpen: true,
      title: 'Approve Memory Lesson',
      message: `Are you sure you want to approve '${item.filename}' into trusted long-term memory?`,
      confirmText: 'Approve Lesson',
      isDestructive: false,
      action: async () => {
        await api.approveMemory(item.id, isEditing ? editingContent : undefined);
        setIsEditing(false);
        loadMemory();
      },
    });
  };

  const handleReject = (item: MemoryItem) => {
    setDialogConfig({
      isOpen: true,
      title: 'Reject Memory Candidate',
      message: `Are you sure you want to reject and archive '${item.filename}'?`,
      confirmText: 'Reject & Archive',
      isDestructive: true,
      action: async () => {
        await api.rejectMemory(item.id, 'User rejected from UI');
        loadMemory();
      },
    });
  };

  const handleArchive = (item: MemoryItem) => {
    setDialogConfig({
      isOpen: true,
      title: 'Archive Approved Note',
      message: `Move '${item.filename}' to Archived? It will be safely excluded from trusted agent retrieval.`,
      confirmText: 'Archive Note',
      isDestructive: true,
      action: async () => {
        await api.archiveMemory(item.id, 'User archived from UI');
        loadMemory();
      },
    });
  };

  const handleRestore = (item: MemoryItem) => {
    setDialogConfig({
      isOpen: true,
      title: 'Restore Lesson to Approved',
      message: `Restore '${item.filename}' back to Approved memory? It will become retrievable again.`,
      confirmText: 'Restore Lesson',
      isDestructive: false,
      action: async () => {
        await api.restoreMemory(item.id);
        loadMemory();
      },
    });
  };

  const handleApplyFix = (finding: HealthFinding) => {
    setDialogConfig({
      isOpen: true,
      title: `Apply Health Recommendation (${finding.suggested_action})`,
      message: `Action '${finding.suggested_action}' will be applied to ${finding.affected_note_ids.join(', ')}. A versioned safety rollback backup will be created in app_data/versioning/.`,
      confirmText: 'Apply Fix',
      isDestructive: false,
      action: async () => {
        await api.applyHealthFix(finding.finding_id);
        handleRunHealthCheck();
      },
    });
  };

  const filteredApproved = memoryData.approved.filter(
    (n) => !searchQuery || n.filename.toLowerCase().includes(searchQuery.toLowerCase()) || n.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%', overflow: 'hidden' }}>
      {/* Left List Column */}
      <div
        style={{
          width: '380px',
          minWidth: '380px',
          borderRight: '1px solid var(--border)',
          backgroundColor: 'var(--surface)',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
        }}
      >
        {/* Navigation Tabs */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid var(--border)',
            backgroundColor: 'var(--sidebar)',
          }}
        >
          {[
            { id: 'approved', label: 'Approved', count: memoryData.approved.length },
            { id: 'pending', label: 'Pending', count: memoryData.pending.length },
            { id: 'health', label: 'Health', count: healthReport ? healthReport.findings.length : undefined },
            { id: 'archived', label: 'Archived', count: memoryData.archived.length },
          ].map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  flex: 1,
                  padding: '12px 6px',
                  fontSize: '12px',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? 'var(--primary)' : 'var(--muted)',
                  borderBottom: `2px solid ${isActive ? 'var(--primary)' : 'transparent'}`,
                  textAlign: 'center',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '4px',
                }}
              >
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span
                    style={{
                      fontSize: '11px',
                      padding: '1px 6px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: isActive ? 'var(--surface)' : 'var(--surface-hover)',
                      border: '1px solid var(--border)',
                      color: isActive ? 'var(--primary)' : 'var(--muted)',
                    }}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Search Bar */}
        {activeTab !== 'health' && (
          <div style={{ padding: '12px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Search size={14} color="var(--muted)" />
              <input
                type="text"
                placeholder="Search notes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  flex: 1,
                  padding: '6px 8px',
                  fontSize: '12px',
                  backgroundColor: 'var(--bg)',
                }}
              />
            </div>
          </div>
        )}

        {/* Tab Item List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
          {activeTab === 'approved' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {filteredApproved.map((item) => {
                const isSelected = selectedNote?.id === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setSelectedNote(item);
                      setIsEditing(false);
                    }}
                    style={{
                      padding: '12px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: isSelected ? 'var(--surface-hover)' : 'transparent',
                      border: `1px solid ${isSelected ? 'var(--primary)' : 'var(--border)'}`,
                      textAlign: 'left',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text)', fontSize: '13px' }}>{item.filename}</span>
                      <span style={{ fontSize: '11px', color: 'var(--muted)' }}>{item.bytes} B</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.preview}
                    </div>
                  </button>
                );
              })}
              {filteredApproved.length === 0 && (
                <EmptyState title="No Approved Memories" description="Verified lessons approved by the human operator will appear here." />
              )}
            </div>
          )}

          {activeTab === 'pending' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {memoryData.pending.map((item) => {
                const isSelected = selectedNote?.id === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setSelectedNote(item);
                      setEditingContent(item.content);
                      setIsEditing(false);
                    }}
                    style={{
                      padding: '12px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: isSelected ? 'var(--surface-hover)' : 'transparent',
                      border: `1px solid ${isSelected ? 'var(--warning)' : 'var(--border)'}`,
                      textAlign: 'left',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 600, color: 'var(--warning)', fontSize: '13px' }}>{item.filename}</span>
                      <StatusBadge status="Pending Review" variant="warning" />
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.preview}
                    </div>
                  </button>
                );
              })}
              {memoryData.pending.length === 0 && (
                <EmptyState title="No Pending Proposals" description="When a verified task produces a high-value lesson (score >= 7), it appears here for human approval." />
              )}
            </div>
          )}

          {activeTab === 'archived' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {memoryData.archived.map((item) => {
                const isSelected = selectedNote?.id === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setSelectedNote(item);
                      setIsEditing(false);
                    }}
                    style={{
                      padding: '12px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: isSelected ? 'var(--surface-hover)' : 'transparent',
                      border: `1px solid ${isSelected ? 'var(--primary)' : 'var(--border)'}`,
                      textAlign: 'left',
                    }}
                  >
                    <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: '13px' }}>{item.filename}</div>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '4px' }}>Archived (Excluded from retrieval)</div>
                  </button>
                );
              })}
              {memoryData.archived.length === 0 && (
                <EmptyState title="No Archived Notes" description="Superceded or retired notes can be archived here rather than hard deleted." />
              )}
            </div>
          )}

          {activeTab === 'health' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                onClick={handleRunHealthCheck}
                disabled={isScanning}
                style={{
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--primary)',
                  color: '#0D1420',
                  fontWeight: 600,
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                }}
              >
                <Stethoscope size={16} />
                <span>{isScanning ? 'Auditing Vault...' : 'Run Memory Health Check'}</span>
              </button>

              {healthReport && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                    Findings ({healthReport.findings.length})
                  </div>
                  {healthReport.findings.map((f) => (
                    <div
                      key={f.finding_id}
                      style={{
                        padding: '12px',
                        borderRadius: 'var(--radius-md)',
                        backgroundColor: 'var(--surface-hover)',
                        border: '1px solid var(--border)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text)' }}>{f.finding_id}</span>
                        <StatusBadge status={f.risk_level} />
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--muted)' }}>{f.reason}</div>
                      <button
                        onClick={() => handleApplyFix(f)}
                        style={{
                          marginTop: '6px',
                          padding: '6px 10px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: 'var(--surface)',
                          border: '1px solid var(--border)',
                          color: 'var(--primary)',
                          fontWeight: 600,
                          fontSize: '11px',
                          alignSelf: 'flex-start',
                        }}
                      >
                        Approve & Apply ({f.suggested_action})
                      </button>
                    </div>
                  ))}
                  {healthReport.findings.length === 0 && (
                    <div style={{ padding: '16px', textAlign: 'center', color: 'var(--success)', fontSize: '13px' }}>
                      Vault is fully healthy. No duplicates, contradictions, or sensitive patterns detected.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right Note Viewer & Editor */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', backgroundColor: 'var(--bg)' }}>
        {selectedNote ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', padding: '24px' }}>
            {/* Note Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '16px',
                paddingBottom: '16px',
                borderBottom: '1px solid var(--border)',
              }}
            >
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text)', marginBottom: '4px' }}>
                  {selectedNote.filename}
                </h2>
                <span style={{ fontSize: '12px', color: 'var(--muted)' }}>
                  Size: {selectedNote.bytes} bytes • Path: 01_Memory/{activeTab === 'approved' ? 'Approved' : (activeTab === 'pending' ? 'Pending' : 'Archived')}/
                </span>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '8px' }}>
                {activeTab === 'approved' && (
                  <button
                    onClick={() => handleArchive(selectedNote)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: 'var(--surface)',
                      border: '1px solid var(--border)',
                      color: 'var(--muted)',
                      fontSize: '12px',
                    }}
                  >
                    <Archive size={14} />
                    <span>Archive</span>
                  </button>
                )}

                {activeTab === 'pending' && (
                  <>
                    <button
                      onClick={() => setIsEditing(!isEditing)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '8px 12px',
                        borderRadius: 'var(--radius-md)',
                        backgroundColor: isEditing ? 'var(--surface-hover)' : 'var(--surface)',
                        border: '1px solid var(--border)',
                        color: 'var(--text)',
                        fontSize: '12px',
                      }}
                    >
                      <Edit3 size={14} />
                      <span>{isEditing ? 'Cancel Edit' : 'Edit Note'}</span>
                    </button>
                    <button
                      onClick={() => handleReject(selectedNote)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '8px 12px',
                        borderRadius: 'var(--radius-md)',
                        backgroundColor: '#2E191B',
                        border: '1px solid var(--error)',
                        color: 'var(--error)',
                        fontSize: '12px',
                        fontWeight: 600,
                      }}
                    >
                      <X size={14} />
                      <span>Reject</span>
                    </button>
                    <button
                      onClick={() => handleApprove(selectedNote)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '8px 14px',
                        borderRadius: 'var(--radius-md)',
                        backgroundColor: 'var(--success)',
                        color: '#0D1420',
                        fontSize: '12px',
                        fontWeight: 600,
                      }}
                    >
                      <Check size={14} />
                      <span>Approve into Memory</span>
                    </button>
                  </>
                )}

                {activeTab === 'archived' && (
                  <button
                    onClick={() => handleRestore(selectedNote)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '8px 14px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: 'var(--primary)',
                      color: '#0D1420',
                      fontSize: '12px',
                      fontWeight: 600,
                    }}
                  >
                    <RotateCcw size={14} />
                    <span>Restore to Approved</span>
                  </button>
                )}
              </div>
            </div>

            {/* Note Body Viewer / Editor */}
            {isEditing ? (
              <textarea
                value={editingContent}
                onChange={(e) => setEditingContent(e.target.value)}
                style={{
                  flex: 1,
                  width: '100%',
                  fontFamily: 'monospace',
                  fontSize: '13px',
                  lineHeight: 1.6,
                  padding: '16px',
                  backgroundColor: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text)',
                  resize: 'none',
                }}
              />
            ) : (
              <pre
                style={{
                  flex: 1,
                  fontFamily: 'monospace',
                  fontSize: '13px',
                  lineHeight: 1.6,
                  padding: '16px',
                  backgroundColor: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text)',
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {selectedNote.content}
              </pre>
            )}
          </div>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <EmptyState icon={FileText} title="Select a Note to Inspect" description="Select any approved lesson, candidate, or conflict to view its contents." />
          </div>
        )}
      </div>

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={dialogConfig.isOpen}
        title={dialogConfig.title}
        message={dialogConfig.message}
        confirmText={dialogConfig.confirmText}
        isDestructive={dialogConfig.isDestructive}
        onConfirm={async () => {
          setDialogConfig((prev) => ({ ...prev, isOpen: false }));
          await dialogConfig.action();
        }}
        onCancel={() => setDialogConfig((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  );
};
