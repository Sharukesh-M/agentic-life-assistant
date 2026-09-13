import React, { useState } from 'react';
import { Task, TaskStatus, TaskPriority } from '../types/api';
import { PlusIcon, CheckIcon } from '../components/Icons';

interface TasksViewProps {
  tasks: Task[];
  onCreateTask: (task: Partial<Task>) => Promise<void>;
  onUpdateTaskStatus: (id: string, status: TaskStatus, notes?: string) => Promise<void>;
}

export const TasksView: React.FC<TasksViewProps> = ({ tasks, onCreateTask, onUpdateTaskStatus }) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [showModal, setShowModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newPriority, setNewPriority] = useState<TaskPriority>('MEDIUM');

  // Verification modal when marking a task complete (Honesty Gate)
  const [completingTask, setCompletingTask] = useState<Task | null>(null);
  const [verificationNotes, setVerificationNotes] = useState('');

  const filteredTasks = statusFilter === 'ALL'
    ? tasks
    : tasks.filter((t) => t.status === statusFilter);

  const handleSubmitNewTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    await onCreateTask({
      title: newTitle,
      description: newDesc,
      priority: newPriority,
      status: 'CREATED',
    });
    setNewTitle('');
    setNewDesc('');
    setShowModal(false);
  };

  const handleConfirmCompletion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!completingTask) return;
    await onUpdateTaskStatus(completingTask.id, 'COMPLETED', verificationNotes);
    setCompletingTask(null);
    setVerificationNotes('');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Action Items</h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Individual actionable tasks with task completion honesty enforcement
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <PlusIcon size={16} />
          <span>Add Action Item</span>
        </button>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '0.375rem', flexWrap: 'wrap', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.625rem' }}>
        {['ALL', 'CREATED', 'IN_PROGRESS', 'COMPLETED', 'SKIPPED'].map((st) => (
          <button
            key={st}
            className="btn btn-secondary btn-sm"
            onClick={() => setStatusFilter(st)}
            style={{
              backgroundColor: statusFilter === st ? 'var(--accent-bg-subtle)' : 'transparent',
              borderColor: statusFilter === st ? 'var(--border-active)' : 'transparent',
              color: statusFilter === st ? 'var(--accent-primary)' : 'var(--text-secondary)',
            }}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Task List Table */}
      {filteredTasks.length === 0 ? (
        <div className="surface-card" style={{ textAlign: 'center', padding: '3rem 1.5rem', color: 'var(--text-muted)' }}>
          <h3>No action items in this view</h3>
          <p style={{ fontSize: '0.8125rem', marginTop: '0.375rem' }}>Create a task to get started.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
          {filteredTasks.map((task) => {
            const isCompleted = task.status === 'COMPLETED';
            return (
              <div
                key={task.id}
                className="surface-card"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.875rem 1.125rem',
                  gap: '1rem',
                  opacity: isCompleted ? 0.7 : 1,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem', flex: 1 }}>
                  {/* Status Toggle Checkbox */}
                  <input
                    type="checkbox"
                    checked={isCompleted}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setCompletingTask(task);
                      } else {
                        onUpdateTaskStatus(task.id, 'IN_PROGRESS');
                      }
                    }}
                    aria-label={`Mark "${task.title}" as complete`}
                    style={{ width: '16px', height: '16px', cursor: 'pointer', accentColor: 'var(--emerald-400)' }}
                  />

                  <div style={{ flex: 1 }}>
                    <div style={{
                      fontWeight: 500,
                      fontSize: '0.875rem',
                      textDecoration: isCompleted ? 'line-through' : 'none',
                      color: isCompleted ? 'var(--text-muted)' : 'var(--text-primary)',
                    }}>
                      {task.title}
                    </div>
                    {task.description && (
                      <div style={{ fontSize: '0.78125rem', color: 'var(--text-secondary)', marginTop: '0.125rem' }}>
                        {task.description}
                      </div>
                    )}
                    {task.honest_verification_notes && (
                      <div style={{ fontSize: '0.725rem', color: 'var(--cyan-400)', marginTop: '0.25rem', fontStyle: 'italic' }}>
                        Honesty verification: "{task.honest_verification_notes}"
                      </div>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className={`badge ${task.priority === 'HIGH' ? 'badge-danger' : task.priority === 'MEDIUM' ? 'badge-warning' : 'badge-neutral'}`}>
                    {task.priority}
                  </span>
                  <span className={`badge ${isCompleted ? 'badge-success' : 'badge-info'}`}>
                    {task.status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Task Completion Honesty Gate Verification Modal */}
      {completingTask && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(7, 10, 18, 0.75)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1.5rem',
        }}>
          <div className="surface-card" style={{ maxWidth: '460px', width: '100%', backgroundColor: 'var(--bg-surface)' }}>
            <h3 style={{ fontSize: '1.05rem', color: 'var(--emerald-400)', marginBottom: '0.375rem' }}>
              Task Completion Honesty Gate
            </h3>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: '1.5' }}>
              JARVIX requires verification notes when marking tasks as complete. Briefly state how or where this was accomplished.
            </p>
            <form onSubmit={handleConfirmCompletion} style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
              <textarea
                className="input-field"
                required
                rows={3}
                placeholder="e.g. 'Implemented feature and verified unit tests clean'"
                value={verificationNotes}
                onChange={(e) => setVerificationNotes(e.target.value)}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.625rem' }}>
                <button className="btn btn-secondary" type="button" onClick={() => setCompletingTask(null)}>Cancel</button>
                <button className="btn btn-primary" type="submit">Verify & Complete Task</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Task Modal */}
      {showModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(7, 10, 18, 0.75)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1.5rem',
        }}>
          <div className="surface-card" style={{ maxWidth: '460px', width: '100%', backgroundColor: 'var(--bg-surface)' }}>
            <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>New Action Item</h2>
            <form onSubmit={handleSubmitNewTask} style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Task Title</label>
                <input
                  className="input-field"
                  required
                  placeholder="Task title"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Description</label>
                <textarea
                  className="input-field"
                  rows={2}
                  placeholder="Additional context..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Priority</label>
                <select className="input-field" value={newPriority} onChange={(e) => setNewPriority(e.target.value as TaskPriority)}>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.625rem', marginTop: '0.5rem' }}>
                <button className="btn btn-secondary" type="button" onClick={() => setShowModal(false)}>Cancel</button>
                <button className="btn btn-primary" type="submit">Create Task</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
