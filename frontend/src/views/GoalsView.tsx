import React, { useState } from 'react';
import { Goal, GoalStatus, TaskPriority } from '../types/api';
import { PlusIcon, TrashIcon, CheckIcon } from '../components/Icons';

interface GoalsViewProps {
  goals: Goal[];
  onCreateGoal: (goal: Partial<Goal>) => Promise<void>;
  onDeleteGoal: (id: string) => Promise<void>;
}

export const GoalsView: React.FC<GoalsViewProps> = ({ goals, onCreateGoal, onDeleteGoal }) => {
  const [activeFilter, setActiveFilter] = useState<GoalStatus | 'ALL'>('ALL');
  const [showModal, setShowModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newCategory, setNewCategory] = useState('Personal Growth');
  const [newPriority, setNewPriority] = useState<TaskPriority>('MEDIUM');

  const filteredGoals = activeFilter === 'ALL'
    ? goals
    : goals.filter((g) => g.status === activeFilter);

  const handleSubmitNewGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    await onCreateGoal({
      title: newTitle,
      description: newDesc,
      category: newCategory,
      priority: newPriority,
      status: 'ACTIVE',
      progress: 0,
      milestones: [],
    });
    setNewTitle('');
    setNewDesc('');
    setShowModal(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header & Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Objectives & Strategy</h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Multi-step goal decomposition, milestone tracking, and long-term progress
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <PlusIcon size={16} />
          <span>New Objective</span>
        </button>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '0.375rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.625rem' }}>
        {(['ALL', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ABANDONED'] as const).map((status) => (
          <button
            key={status}
            className="btn btn-secondary btn-sm"
            onClick={() => setActiveFilter(status)}
            style={{
              backgroundColor: activeFilter === status ? 'var(--accent-bg-subtle)' : 'transparent',
              borderColor: activeFilter === status ? 'var(--border-active)' : 'transparent',
              color: activeFilter === status ? 'var(--accent-primary)' : 'var(--text-secondary)',
            }}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Goal Items Timeline / List */}
      {filteredGoals.length === 0 ? (
        <div className="surface-card" style={{ textAlign: 'center', padding: '3rem 1.5rem', color: 'var(--text-muted)' }}>
          <h3>No objectives recorded in this view</h3>
          <p style={{ fontSize: '0.8125rem', marginTop: '0.375rem' }}>
            Click "New Objective" or prompt JARVIX in Chat to decompose a goal into actionable steps.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {filteredGoals.map((goal) => (
            <div key={goal.id} className="surface-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <span className="badge badge-neutral" style={{ fontSize: '0.65rem' }}>
                      {goal.category || 'General'}
                    </span>
                    <span className={`badge ${goal.status === 'ACTIVE' ? 'badge-success' : 'badge-neutral'}`}>
                      {goal.status}
                    </span>
                    <span className={`badge ${goal.priority === 'HIGH' ? 'badge-danger' : 'badge-info'}`}>
                      {goal.priority} Priority
                    </span>
                  </div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>{goal.title}</h3>
                </div>

                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onDeleteGoal(goal.id)}
                  title="Remove Goal"
                  style={{ color: 'var(--status-danger)' }}
                >
                  <TrashIcon size={14} />
                </button>
              </div>

              {goal.description && (
                <p style={{ fontSize: '0.84375rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                  {goal.description}
                </p>
              )}

              {/* Progress Bar & Milestones */}
              <div style={{ paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.375rem' }}>
                  <span>Milestone Progression</span>
                  <span>{goal.progress || 0}% Complete</span>
                </div>
                <div style={{ width: '100%', height: '4px', backgroundColor: 'var(--slate-800)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                  <div style={{ width: `${goal.progress || 0}%`, height: '100%', backgroundColor: 'var(--emerald-400)' }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Goal Creation Modal */}
      {showModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(7, 10, 18, 0.75)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1.5rem',
        }}>
          <div className="surface-card" style={{ maxWidth: '480px', width: '100%', backgroundColor: 'var(--bg-surface)' }}>
            <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Define New Objective</h2>
            <form onSubmit={handleSubmitNewGoal} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Goal Title</label>
                <input
                  className="input-field"
                  required
                  placeholder="e.g. Complete Rust Memory Safety Course"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Description</label>
                <textarea
                  className="input-field"
                  rows={3}
                  placeholder="Define target outcomes..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Category</label>
                  <input
                    className="input-field"
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Priority</label>
                  <select
                    className="input-field"
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value as TaskPriority)}
                  >
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.625rem', marginTop: '0.5rem' }}>
                <button className="btn btn-secondary" type="button" onClick={() => setShowModal(false)}>Cancel</button>
                <button className="btn btn-primary" type="submit">Save Objective</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
