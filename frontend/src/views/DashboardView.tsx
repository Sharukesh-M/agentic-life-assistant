import React, { useState } from 'react';
import { Goal, Task, NotificationItem } from '../types/api';
import { GoalsIcon, TasksIcon, InsightsIcon, SendIcon, CheckIcon } from '../components/Icons';

interface DashboardViewProps {
  goals: Goal[];
  tasks: Task[];
  notifications: NotificationItem[];
  onNavigate: (tab: string) => void;
  onSendQuickChat: (msg: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  goals,
  tasks,
  notifications,
  onNavigate,
  onSendQuickChat,
}) => {
  const [quickInput, setQuickInput] = useState('');

  const activeGoals = goals.filter((g) => g.status === 'ACTIVE');
  const pendingTasks = tasks.filter((t) => t.status !== 'COMPLETED' && t.status !== 'SKIPPED');
  const unreadNotifications = notifications.filter((n) => !n.read && !n.dismissed);

  const primaryGoal = activeGoals[0];
  const topInsight = unreadNotifications[0];

  const handleQuickSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickInput.trim()) return;
    onSendQuickChat(quickInput);
    onNavigate('chat');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* Header & Quick Interaction */}
      <div className="surface-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.25rem' }}>
            System Focus Overview
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            JARVIX is monitoring active objectives, scheduled action items, and system context.
          </p>
        </div>

        {/* Quick Assistant Command Bar */}
        <form onSubmit={handleQuickSubmit} style={{ display: 'flex', gap: '0.625rem' }}>
          <input
            className="input-field"
            type="text"
            placeholder="Instruct JARVIX (e.g. 'Break down my study goal', 'Show top priority action items')"
            value={quickInput}
            onChange={(e) => setQuickInput(e.target.value)}
          />
          <button className="btn btn-primary" type="submit" disabled={!quickInput.trim()}>
            <span>Ask</span>
            <SendIcon size={14} />
          </button>
        </form>
      </div>

      {/* Overview Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <div className="surface-card" onClick={() => onNavigate('goals')} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '0.625rem', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent-primary)' }}>
            <GoalsIcon size={20} />
          </div>
          <div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{activeGoals.length}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Active Goals</div>
          </div>
        </div>

        <div className="surface-card" onClick={() => onNavigate('tasks')} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '0.625rem', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(245, 158, 11, 0.1)', color: 'var(--warning-400)' }}>
            <TasksIcon size={20} />
          </div>
          <div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{pendingTasks.length}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Pending Action Items</div>
          </div>
        </div>

        <div className="surface-card" onClick={() => onNavigate('notifications')} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '0.625rem', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(6, 182, 212, 0.1)', color: 'var(--cyan-400)' }}>
            <InsightsIcon size={20} />
          </div>
          <div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{unreadNotifications.length}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Unread Insights</div>
          </div>
        </div>
      </div>

      {/* Proactive Recommendation Banner (if available) */}
      {topInsight && (
        <div className="surface-card" style={{ borderLeft: '4px solid var(--cyan-400)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>Proactive Recommendation</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{topInsight.category}</span>
            </div>
            <h3 style={{ fontSize: '0.9375rem', fontWeight: 600 }}>{topInsight.title}</h3>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '0.125rem' }}>{topInsight.message}</p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('notifications')}>
            Review Insight
          </button>
        </div>
      )}

      {/* Two Column Section: Primary Goal & Pending Priorities */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.25rem' }}>
        {/* Primary Focus Goal */}
        <div className="surface-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '1.05rem' }}>Primary Goal Focus</h2>
            <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('goals')}>
              View All Goals →
            </button>
          </div>

          {!primaryGoal ? (
            <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              <p style={{ fontSize: '0.875rem' }}>No active goals tracked.</p>
              <p style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>Start a chat with JARVIX to define your first objective.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.375rem' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>{primaryGoal.title}</h3>
                  <span className={`badge ${primaryGoal.priority === 'HIGH' ? 'badge-danger' : 'badge-neutral'}`}>
                    {primaryGoal.priority} Priority
                  </span>
                </div>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                  {primaryGoal.description || 'Active multi-step objective.'}
                </p>
              </div>

              {/* Goal Milestone Progression */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.375rem' }}>
                  <span>Progression</span>
                  <span>{primaryGoal.progress || 0}%</span>
                </div>
                <div style={{ width: '100%', height: '4px', backgroundColor: 'var(--slate-800)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                  <div style={{ width: `${primaryGoal.progress || 0}%`, height: '100%', backgroundColor: 'var(--emerald-400)' }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Priority Action Items */}
        <div className="surface-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '1.05rem' }}>Upcoming Action Items</h2>
            <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('tasks')}>
              View All Tasks →
            </button>
          </div>

          {pendingTasks.length === 0 ? (
            <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              <p style={{ fontSize: '0.875rem' }}>All action items are up to date.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {pendingTasks.slice(0, 4).map((task) => (
                <div
                  key={task.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.625rem 0.875rem',
                    backgroundColor: 'var(--bg-surface-elevated)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                    <CheckIcon size={14} color={task.priority === 'HIGH' ? 'var(--status-danger)' : 'var(--text-muted)'} />
                    <span style={{ fontSize: '0.84375rem', fontWeight: 500 }}>{task.title}</span>
                  </div>
                  <span className={`badge ${task.priority === 'HIGH' ? 'badge-danger' : 'badge-neutral'}`} style={{ fontSize: '0.65rem' }}>
                    {task.priority}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
