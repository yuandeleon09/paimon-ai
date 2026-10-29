import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Loader2,
  Users,
  Lightbulb,
  AlertCircle,
  Plus,
  PanelRightClose,
  PanelRightOpen,
  ShieldCheck,
  Paperclip,
  Image as ImageIcon,
  FileText,
  FileSpreadsheet,
  FileCode,
  X,
  FileCheck
} from 'lucide-react';
import { api } from '../../services/api';
import type { Message, Conversation, ChatTaskResult } from '../../services/types';
import { StatusBadge } from '../../components/StatusBadge';
import { EmptyState } from '../../components/EmptyState';

const SUPPORTED_EXTS = new Set([
  '.png', '.jpg', '.jpeg', '.webp',
  '.pdf',
  '.docx', '.xlsx', '.pptx',
  '.txt', '.md', '.csv', '.json', '.py', '.js', '.ts',
  '.tsx', '.jsx', '.html', '.css', '.yaml', '.yml',
  '.xml', '.log', '.sql'
]);

const MAX_ATTACHMENTS = 4;
const MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024; // 8 MB
const MAX_TOTAL_SIZE_BYTES = 12 * 1024 * 1024; // 12 MB

const getFileIcon = (filename: string) => {
  const ext = '.' + (filename.split('.').pop() || '').toLowerCase();
  if (['.png', '.jpg', '.jpeg', '.webp'].includes(ext)) {
    return <ImageIcon size={14} color="var(--primary)" />;
  }
  if (ext === '.xlsx') {
    return <FileSpreadsheet size={14} color="var(--primary)" />;
  }
  if (['.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.json', '.sql'].includes(ext)) {
    return <FileCode size={14} color="var(--primary)" />;
  }
  return <FileText size={14} color="var(--primary)" />;
};

interface ChatPageProps {
  projectId: string;
  onOpenMemory?: (noteId: string) => void;
  isConnected: boolean;
}

export const ChatPage: React.FC<ChatPageProps> = ({
  projectId,
  isConnected,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputPrompt, setInputPrompt] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [lastResult, setLastResult] = useState<ChatTaskResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [collaborativeMode, setCollaborativeMode] = useState<boolean>(true);
  const [showActivity, setShowActivity] = useState<boolean>(true);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, [projectId]);

  // Load messages when active conversation changes
  useEffect(() => {
    if (activeConvId) {
      loadMessages(activeConvId);
    }
  }, [activeConvId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const loadConversations = async () => {
    try {
      const res = await api.listConversations(projectId);
      setConversations(res.conversations);
      if (res.conversations.length > 0 && !activeConvId) {
        setActiveConvId(res.conversations[0].id);
      } else if (res.conversations.length === 0) {
        handleNewSession();
      }
    } catch {
      if (!activeConvId) {
        const fallbackId = `local-${Date.now()}`;
        setActiveConvId(fallbackId);
      }
    }
  };

  const loadMessages = async (convId: string) => {
    try {
      const res = await api.getMessages(convId);
      setMessages(res.messages);
    } catch {
      // ignore
    }
  };

  const handleNewSession = async () => {
    try {
      const res = await api.createConversation('New Task Session', projectId);
      setActiveConvId(res.conversation_id);
      setMessages([]);
      setLastResult(null);
      setErrorMsg(null);
      setAttachments([]);
      loadConversations();
    } catch {
      const fallbackId = `local-${Date.now()}`;
      setActiveConvId(fallbackId);
      setMessages([]);
    }
  };

  const handleAddFiles = (incoming: File[]) => {
    setErrorMsg(null);
    if (!incoming || incoming.length === 0) return;

    if (attachments.length + incoming.length > MAX_ATTACHMENTS) {
      setErrorMsg(`Maximum ${MAX_ATTACHMENTS} attachments allowed per task.`);
      return;
    }

    const nextFiles = [...attachments];
    for (const f of incoming) {
      const ext = '.' + (f.name.split('.').pop() || '').toLowerCase();
      if (!SUPPORTED_EXTS.has(ext)) {
        setErrorMsg(`Unsupported file type '${ext}' for '${f.name}'. Supported: images (PNG/JPG/WEBP), PDF, Word (DOCX), Excel (XLSX), PowerPoint (PPTX), and plain text/code.`);
        return;
      }
      if (f.size > MAX_FILE_SIZE_BYTES) {
        setErrorMsg(`File '${f.name}' (${(f.size / (1024 * 1024)).toFixed(1)} MB) exceeds the 8 MB maximum size limit.`);
        return;
      }
      if (nextFiles.some((existing) => existing.name === f.name)) {
        continue;
      }
      nextFiles.push(f);
    }

    const totalBytes = nextFiles.reduce((acc, cur) => acc + cur.size, 0);
    if (totalBytes > MAX_TOTAL_SIZE_BYTES) {
      setErrorMsg(`Combined attachments (${(totalBytes / (1024 * 1024)).toFixed(1)} MB) exceed the 12 MB media limit.`);
      return;
    }

    setAttachments(nextFiles);
  };

  const handleRemoveFile = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleAddFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    if (e.clipboardData && e.clipboardData.items) {
      const items = Array.from(e.clipboardData.items);
      const imageFiles: File[] = [];
      for (const item of items) {
        if (item.kind === 'file' && item.type.startsWith('image/')) {
          const file = item.getAsFile();
          if (file) {
            const ext = item.type.split('/')[1] || 'png';
            const pastedFile = new File([file], `screenshot-${Date.now()}.${ext}`, { type: file.type });
            imageFiles.push(pastedFile);
          }
        }
      }
      if (imageFiles.length > 0) {
        handleAddFiles(imageFiles);
      }
    }
  };

  const handleSend = async () => {
    let text = inputPrompt.trim();
    if (!text && attachments.length === 0) return;
    if (isLoading) return;

    if (!text && attachments.length > 0) {
      text = "Please analyze the attached files and summarize findings or resolve visible issues.";
    }

    if (!isConnected) {
      setErrorMsg('Backend server is offline. Please start the Python backend (server.py) on http://127.0.0.1:8000.');
      return;
    }

    setErrorMsg(null);
    setInputPrompt('');
    const filesToSend = [...attachments];
    setAttachments([]);
    setIsLoading(true);

    let displayContent = text;
    if (filesToSend.length > 0) {
      const fileNames = filesToSend.map((f) => `📎 ${f.name} (${(f.size / 1024).toFixed(0)} KB)`).join(', ');
      displayContent = `[Attached: ${fileNames}]\n\n${text}`;
    }

    // Optimistically add user message
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConvId,
      role: 'user',
      content: displayContent,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await api.sendChat(
        {
          task: text,
          project_id: projectId,
          conversation_id: activeConvId,
          collaborative: collaborativeMode,
          allow_revise: true,
        },
        filesToSend
      );

      setLastResult(res);

      // Add final assistant message
      const assistantMsg: Message = {
        id: `asst-${Date.now()}`,
        conversation_id: activeConvId,
        role: 'assistant',
        content: res.result,
        agent_name: 'orchestrator',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setErrorMsg(err.message || 'Task execution failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%', overflow: 'hidden' }}>
      {/* Session List Mini Column */}
      <div
        style={{
          width: '200px',
          minWidth: '200px',
          borderRight: '1px solid var(--border)',
          backgroundColor: 'var(--bg)',
          display: 'flex',
          flexDirection: 'column',
          padding: '12px',
        }}
      >
        <button
          onClick={handleNewSession}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '8px 12px',
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--text)',
            fontWeight: 600,
            fontSize: '12px',
            marginBottom: '12px',
          }}
        >
          <Plus size={14} color="var(--primary)" />
          <span>New Session</span>
        </button>

        <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '8px', paddingLeft: '4px' }}>
          Recent Sessions
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {conversations.map((c) => {
            const isActive = c.id === activeConvId;
            return (
              <button
                key={c.id}
                onClick={() => setActiveConvId(c.id)}
                style={{
                  padding: '8px 10px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: isActive ? 'var(--surface-hover)' : 'transparent',
                  border: `1px solid ${isActive ? 'var(--border)' : 'transparent'}`,
                  color: isActive ? 'var(--text)' : 'var(--muted)',
                  fontSize: '12px',
                  textAlign: 'left',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {c.title}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Conversation Center */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onPaste={handlePaste}
        style={{
          position: 'relative',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden'
        }}
      >
        {/* Drag Overlay */}
        {isDragging && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(13, 20, 32, 0.9)',
              border: '2px dashed var(--primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 100,
              pointerEvents: 'none',
              color: 'var(--text)',
              fontSize: '15px',
              fontWeight: 600,
              gap: '10px'
            }}
          >
            <Paperclip size={22} color="var(--primary)" />
            <span>Drop files here to attach (Max 4 files, 8 MB each)</span>
          </div>
        )}

        {/* Chat Header Options */}
        <div
          style={{
            padding: '10px 20px',
            borderBottom: '1px solid var(--border)',
            backgroundColor: 'var(--surface)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={collaborativeMode}
              onChange={(e) => setCollaborativeMode(e.target.checked)}
              style={{ accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
            <span style={{ fontWeight: 500, color: 'var(--text)' }}>
              🤝 Collaborative Team Room (Multi-Agent Synthesis)
            </span>
          </label>

          <button
            onClick={() => setShowActivity(!showActivity)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border)',
              backgroundColor: 'var(--surface-hover)',
              color: 'var(--muted)',
              fontSize: '12px',
            }}
          >
            {showActivity ? <PanelRightClose size={14} /> : <PanelRightOpen size={14} />}
            <span>{showActivity ? 'Hide Activity' : 'Show Activity'}</span>
          </button>
        </div>

        {/* Message Thread */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {messages.length === 0 && !isLoading && (
            <EmptyState
              icon={Users}
              title="Your AI Specialist Team is Ready"
              description="Ask a goal or engineering question, or attach screenshots, PDFs, Word, Excel, PowerPoint, and code files. Planner, Developer, Reviewer, and Tester will coordinate to formulate verified answers."
            />
          )}

          {messages.map((m) => {
            const isUser = m.role === 'user';
            return (
              <div
                key={m.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: isUser ? 'flex-end' : 'flex-start',
                  width: '100%',
                }}
              >
                <div
                  style={{
                    fontSize: '11px',
                    color: 'var(--muted)',
                    marginBottom: '4px',
                    padding: '0 4px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{isUser ? 'You' : (m.agent_name || 'Orchestrator Team')}</span>
                  <span>{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>

                <div
                  style={{
                    maxWidth: '85%',
                    padding: '14px 18px',
                    borderRadius: 'var(--radius-lg)',
                    backgroundColor: isUser ? 'var(--surface-hover)' : 'var(--surface)',
                    border: `1px solid ${isUser ? 'var(--primary)' : 'var(--border)'}`,
                    color: 'var(--text)',
                    fontSize: '14px',
                    lineHeight: 1.6,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {m.content}
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                width: 'fit-content',
                color: 'var(--muted)',
                fontSize: '13px',
              }}
            >
              <Loader2 size={16} color="var(--primary)" className="spin" />
              <span>Agents collaborating: Attachment Analyst extracting evidence, Planner structuring, Developer executing...</span>
            </div>
          )}

          {errorMsg && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: '#2E191B',
                border: '1px solid var(--error)',
                color: 'var(--error)',
                fontSize: '13px',
              }}
            >
              <AlertCircle size={16} />
              <span>{errorMsg}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Composer (Sticky at bottom) */}
        <div
          style={{
            padding: '16px 20px',
            backgroundColor: 'var(--bg)',
            borderTop: '1px solid var(--border)',
          }}
        >
          {/* Removable Attachment Preview Chips */}
          {attachments.length > 0 && (
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '10px',
                padding: '8px 12px',
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              {attachments.map((file, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 8px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'var(--surface-hover)',
                    border: '1px solid var(--border)',
                    fontSize: '12px',
                    color: 'var(--text)',
                  }}
                >
                  {getFileIcon(file.name)}
                  <span
                    style={{
                      maxWidth: '160px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      fontWeight: 500,
                    }}
                    title={file.name}
                  >
                    {file.name}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--muted)' }}>
                    ({(file.size / 1024).toFixed(0)} KB)
                  </span>
                  <button
                    onClick={() => handleRemoveFile(idx)}
                    title="Remove attachment"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '2px',
                      background: 'none',
                      border: 'none',
                      color: 'var(--muted)',
                      cursor: 'pointer',
                    }}
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
              <div style={{ fontSize: '11px', color: 'var(--muted)', alignSelf: 'center', marginLeft: 'auto' }}>
                {attachments.length} / {MAX_ATTACHMENTS} files
              </div>
            </div>
          )}

          <div
            style={{
              display: 'flex',
              alignItems: 'flex-end',
              gap: '8px',
              backgroundColor: 'var(--surface)',
              border: `1px solid ${isDragging ? 'var(--primary)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-md)',
              padding: '8px 12px',
            }}
          >
            {/* Paperclip Button */}
            <input
              type="file"
              ref={fileInputRef}
              multiple
              onChange={(e) => {
                if (e.target.files) {
                  handleAddFiles(Array.from(e.target.files));
                }
                e.target.value = '';
              }}
              accept=".png,.jpg,.jpeg,.webp,.pdf,.docx,.xlsx,.pptx,.txt,.md,.csv,.json,.py,.js,.ts,.tsx,.jsx,.html,.css,.yaml,.yml,.xml,.log,.sql"
              style={{ display: 'none' }}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading || attachments.length >= MAX_ATTACHMENTS}
              title={`Attach files (Max ${MAX_ATTACHMENTS} files, 8 MB each)`}
              aria-label="Attach files"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '36px',
                height: '36px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'transparent',
                border: '1px solid var(--border)',
                color: attachments.length >= MAX_ATTACHMENTS ? 'var(--muted)' : 'var(--text)',
                cursor: attachments.length >= MAX_ATTACHMENTS ? 'not-allowed' : 'pointer',
              }}
            >
              <Paperclip size={16} />
            </button>

            <textarea
              ref={textareaRef}
              rows={2}
              placeholder={attachments.length > 0 ? "Ask a question about these attachments... (or press Send to summarize)" : "Ask your AI team... (Enter to send, Shift+Enter for newline, Ctrl+V to paste screenshot)"}
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              style={{
                flex: 1,
                border: 'none',
                backgroundColor: 'transparent',
                resize: 'none',
                padding: '4px',
                fontSize: '14px',
                color: 'var(--text)',
                outline: 'none',
              }}
            />

            <button
              onClick={handleSend}
              disabled={isLoading || (!inputPrompt.trim() && attachments.length === 0)}
              title="Send task"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '36px',
                height: '36px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: (inputPrompt.trim() || attachments.length > 0) && !isLoading ? 'var(--primary)' : 'var(--surface-hover)',
                color: (inputPrompt.trim() || attachments.length > 0) && !isLoading ? '#0D1420' : 'var(--muted)',
                fontWeight: 600,
              }}
            >
              {isLoading ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
            </button>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '11px', color: 'var(--muted)' }}>
            <span>Zero-cost Gemini 3.5 Flash-Lite • Quota safety cap 8 calls/task</span>
            <span>Attachments: images, PDF, Word, Excel, PPT, text/code</span>
          </div>
        </div>
      </div>

      {/* Right Contextual Activity & Team Idea Panel */}
      {showActivity && (
        <div
          style={{
            width: '320px',
            minWidth: '320px',
            borderLeft: '1px solid var(--border)',
            backgroundColor: 'var(--sidebar)',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            overflowY: 'auto',
            padding: '16px',
          }}
        >
          <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={16} color="var(--primary)" />
            <span>Agent Activity & Team Synthesis</span>
          </div>

          {lastResult ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Task Verdict */}
              <div
                style={{
                  padding: '12px',
                  backgroundColor: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--muted)' }}>Run ID: {lastResult.run_id.slice(0, 8)}</span>
                  <StatusBadge status={lastResult.verdict} />
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text)' }}>
                  Calls used: <strong>{lastResult.run_metadata?.api_calls || 1}</strong> / 8
                </div>
              </div>

              {/* Execution Steps */}
              <div>
                <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                  Workflow Pipeline
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {lastResult.steps.map((st, i) => (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 10px',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: 'var(--surface)',
                        border: '1px solid var(--border)',
                        fontSize: '12px',
                      }}
                    >
                      <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{st.agent}</span>
                      <StatusBadge status={st.status} />
                    </div>
                  ))}
                </div>
              </div>

              {/* Attached Evidence Details */}
              {lastResult.attachments && lastResult.attachments.length > 0 && (
                <div
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'var(--surface)',
                    border: '1px solid var(--border)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--primary)', marginBottom: '8px', fontSize: '12px', fontWeight: 700 }}>
                    <FileCheck size={16} />
                    <span>Processed Attachment Evidence</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '8px' }}>
                    {lastResult.attachments.map((att, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: '11px',
                          color: 'var(--text)',
                          padding: '4px 6px',
                          backgroundColor: 'var(--surface-hover)',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '180px' }}>
                          📄 {att.filename}
                        </span>
                        <span style={{ color: 'var(--muted)' }}>
                          {(att.size_bytes / 1024).toFixed(0)} KB
                        </span>
                      </div>
                    ))}
                  </div>
                  {lastResult.attachment_warnings && lastResult.attachment_warnings.length > 0 && (
                    <div style={{ padding: '6px 8px', borderRadius: 'var(--radius-sm)', backgroundColor: '#2E191B', border: '1px solid var(--error)', fontSize: '11px', color: 'var(--error)' }}>
                      <strong>Extraction Limitations:</strong>
                      <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                        {lastResult.attachment_warnings.map((w, wi) => (
                          <li key={wi}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Team Idea Card */}
              {lastResult.team_idea && (
                <div
                  style={{
                    padding: '14px',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'var(--surface)',
                    border: '1px solid var(--border)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--primary)', marginBottom: '8px', fontSize: '12px', fontWeight: 700 }}>
                    <Lightbulb size={16} />
                    <span>Team Collaboration Idea</span>
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text)', marginBottom: '6px' }}>
                    {lastResult.team_idea.title}
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.5, marginBottom: '8px' }}>
                    {lastResult.team_idea.synthesis}
                  </p>
                  {lastResult.team_idea.conflicts_detected && lastResult.team_idea.conflicts_detected.length > 0 && (
                    <div style={{ marginTop: '8px', padding: '6px 8px', borderRadius: 'var(--radius-sm)', backgroundColor: '#2E191B', border: '1px solid var(--error)', fontSize: '11px', color: 'var(--error)' }}>
                      Contradictions Preserved: {lastResult.team_idea.conflicts_detected.join(', ')}
                    </div>
                  )}
                </div>
              )}

              {/* Memory Assessment */}
              {lastResult.memory_decision && (
                <div
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'var(--surface)',
                    border: '1px solid var(--border)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--success)', marginBottom: '6px', fontSize: '12px', fontWeight: 700 }}>
                    <ShieldCheck size={16} />
                    <span>Selective Memory Assessment</span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text)', marginBottom: '4px' }}>
                    Value Score: <strong>{lastResult.memory_decision.score}/10</strong> (Threshold: 7)
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--muted)', lineHeight: 1.4 }}>
                    {lastResult.memory_decision.rationale}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--muted)', fontSize: '12px' }}>
              No active task run. Submit a prompt or attach files to view live agent step contributions and team ideas.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
