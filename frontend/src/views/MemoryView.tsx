import React, { useState } from 'react';
import { MemoryPreference } from '../types/api';
import { PlusIcon, TrashIcon } from '../components/Icons';

interface MemoryViewProps {
  preferences: MemoryPreference[];
  onSavePreference: (key: string, value: string, category?: string) => Promise<void>;
  onDeletePreference: (key: string) => Promise<void>;
}

export const MemoryView: React.FC<MemoryViewProps> = ({ preferences, onSavePreference, onDeletePreference }) => {
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [newCategory, setNewCategory] = useState('user_preference');

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim() || !newValue.trim()) return;
    await onSavePreference(newKey, newValue, newCategory);
    setNewKey('');
    setNewValue('');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Tiered Memory System</h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          User-manageable standing directives and assistant behavioral preferences
        </p>
      </div>

      {/* Safety Notice Banner */}
      <div className="surface-card" style={{ borderLeft: '3px solid var(--cyan-400)', backgroundColor: 'var(--bg-surface-subtle)' }}>
        <h3 style={{ fontSize: '0.9375rem', color: 'var(--cyan-400)', marginBottom: '0.25rem' }}>
          Memory System Architecture
        </h3>
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
          Per JARVIX memory classification specifications, vector embeddings and internal execution logs remain in durable system storage.
          Only explicit user preferences and standing guidelines are editable here.
        </p>
      </div>

      {/* Add Preference Form */}
      <div className="surface-card">
        <h3 style={{ fontSize: '1rem', marginBottom: '0.875rem' }}>Set Explicit Directive</h3>
        <form onSubmit={handleAdd} style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr auto', gap: '0.625rem', alignItems: 'flex-end' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.725rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Key Identifier</label>
            <input className="input-field" placeholder="e.g. preferred_stack" value={newKey} onChange={(e) => setNewKey(e.target.value)} required />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.725rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Value / Guideline</label>
            <input className="input-field" placeholder="e.g. Prefer TypeScript and Python for code responses" value={newValue} onChange={(e) => setNewValue(e.target.value)} required />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.725rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Category</label>
            <input className="input-field" value={newCategory} onChange={(e) => setNewCategory(e.target.value)} />
          </div>
          <button className="btn btn-primary" type="submit">
            <PlusIcon size={14} />
            <span>Save</span>
          </button>
        </form>
      </div>

      {/* Stored Preferences List */}
      <div className="surface-card">
        <h3 style={{ fontSize: '1rem', marginBottom: '0.875rem' }}>Active User Preferences ({preferences.length})</h3>
        {preferences.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', padding: '1rem 0' }}>
            No custom directives stored yet. Add one above or tell JARVIX in chat.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
            {preferences.map((pref) => (
              <div
                key={pref.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.75rem 1rem',
                  backgroundColor: 'var(--bg-surface-elevated)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: 'var(--accent-primary)' }}>
                      {pref.key}
                    </span>
                    <span className="badge badge-neutral" style={{ fontSize: '0.625rem' }}>{pref.category}</span>
                  </div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                    {pref.value}
                  </div>
                </div>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onDeletePreference(pref.key)}
                  style={{ color: 'var(--status-danger)' }}
                  title="Remove Directive"
                >
                  <TrashIcon size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
