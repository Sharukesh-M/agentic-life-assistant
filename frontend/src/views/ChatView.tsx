import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../types/api';
import { AgentActivityIndicator } from '../components/AgentActivityIndicator';
import { ConfirmationModal } from '../components/ConfirmationModal';
import { SendIcon } from '../components/Icons';

interface ChatViewProps {
  messages: ChatMessage[];
  onSendMessage: (msg: string) => Promise<void>;
  isLoading: boolean;
  initialInput?: string;
}

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  onSendMessage,
  isLoading,
  initialInput = '',
}) => {
  const [input, setInput] = useState(initialInput);
  const [confirmModalData, setConfirmModalData] = useState<{ isOpen: boolean; title: string; message: string; action?: string } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    const textToSend = input;
    setInput('');
    await onSendMessage(textToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - var(--topbar-height) - 4rem)', gap: '1rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>JARVIX Goal Agent Interface</h1>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            Goal-aware orchestration, action item extraction, and memory alignment
          </p>
        </div>
        <span className="badge badge-info">Multi-Agent Pipeline</span>
      </div>

      {/* Messages Feed */}
      <div
        role="log"
        aria-live="polite"
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1.25rem',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
        }}
      >
        {messages.length === 0 ? (
          <div style={{ margin: 'auto', textAlign: 'center', maxWidth: '440px', color: 'var(--text-muted)' }}>
            <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem', fontSize: '1.1rem' }}>
              How can JARVIX assist your goals today?
            </h3>
            <p style={{ fontSize: '0.84375rem', lineHeight: '1.5' }}>
              You can define a new objective (e.g. "Plan a 30-day learning path for Rust"), ask for action item status, or request a proactive priority check.
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.sender === 'user';
            return (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: isUser ? 'flex-end' : 'flex-start',
                  maxWidth: '85%',
                  alignSelf: isUser ? 'flex-end' : 'flex-start',
                  gap: '0.375rem',
                }}
              >
                <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                  {isUser ? 'You' : 'JARVIX Assistant'} • {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>

                <div
                  style={{
                    padding: '0.875rem 1.125rem',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: isUser ? 'var(--accent-bg-subtle)' : 'var(--bg-surface-elevated)',
                    border: `1px solid ${isUser ? 'var(--border-active)' : 'var(--border-color)'}`,
                    color: 'var(--text-primary)',
                    fontSize: '0.875rem',
                    lineHeight: '1.6',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {msg.content}
                </div>

                {/* Render Agent Execution Step Trace */}
                {!isUser && msg.agent_trace && (
                  <div style={{ width: '100%', marginTop: '0.25rem' }}>
                    <AgentActivityIndicator
                      intent={msg.agent_trace.intent}
                      steps={msg.agent_trace.steps_executed}
                      isExecuting={false}
                    />
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Processing Indicator */}
        {isLoading && (
          <div style={{ alignSelf: 'flex-start', maxWidth: '80%' }}>
            <AgentActivityIndicator isExecuting={true} />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Message Composer */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.625rem' }}>
        <textarea
          className="input-field"
          placeholder="Instruct JARVIX... (Enter to send, Shift+Enter for new line)"
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          style={{ resize: 'none' }}
        />
        <button
          className="btn btn-primary"
          type="submit"
          disabled={isLoading || !input.trim()}
          style={{ minWidth: '90px' }}
        >
          <span>Send</span>
          <SendIcon size={14} />
        </button>
      </form>

      {/* Confirmation Modal Handler */}
      {confirmModalData && (
        <ConfirmationModal
          isOpen={confirmModalData.isOpen}
          title={confirmModalData.title}
          message={confirmModalData.message}
          actionName={confirmModalData.action}
          onConfirm={() => {
            setConfirmModalData(null);
            onSendMessage(`[CONFIRMED] User authorized action: ${confirmModalData.action}`);
          }}
          onCancel={() => setConfirmModalData(null)}
        />
      )}
    </div>
  );
};
