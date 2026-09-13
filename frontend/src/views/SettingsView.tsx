import React from 'react';
import { SunIcon, MoonIcon, TrashIcon } from '../components/Icons';

interface SettingsViewProps {
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
  backendOnline: boolean;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ theme, setTheme, backendOnline }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '760px', margin: '0 auto', width: '100%' }}>
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Settings & Telemetry</h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Environment state, appearance theme, and backend subsystem health
        </p>
      </div>

      {/* Appearance Section */}
      <div className="surface-card">
        <h3 style={{ fontSize: '1rem', marginBottom: '0.875rem' }}>Appearance Theme</h3>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            className={`btn ${theme === 'dark' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setTheme('dark')}
          >
            <MoonIcon size={14} />
            <span>Dark Mode (Default)</span>
          </button>
          <button
            className={`btn ${theme === 'light' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setTheme('light')}
          >
            <SunIcon size={14} />
            <span>Light Mode (High Contrast)</span>
          </button>
        </div>
      </div>

      {/* Backend Subsystems Telemetry */}
      <div className="surface-card">
        <h3 style={{ fontSize: '1rem', marginBottom: '0.875rem' }}>Backend Telemetry & Infrastructure</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.625rem 0.875rem', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.84375rem' }}>FastAPI Server Connection (:8000)</span>
            <span className={`badge ${backendOnline ? 'badge-success' : 'badge-danger'}`}>
              {backendOnline ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.625rem 0.875rem', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.84375rem' }}>Database Layer</span>
            <span className="badge badge-success">SQLAlchemy / PostgreSQL / SQLite / InMemory</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.625rem 0.875rem', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.84375rem' }}>Tool Registry & Safety Engine</span>
            <span className="badge badge-info">Authorization Gated</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.625rem 0.875rem', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.84375rem' }}>MCP Adapter Pipeline</span>
            <span className="badge badge-neutral">Ready / Mock Transports</span>
          </div>
        </div>
      </div>

      {/* Local Session & Reset */}
      <div className="surface-card">
        <h3 style={{ fontSize: '1rem', marginBottom: '0.375rem' }}>Client Session</h3>
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '0.875rem' }}>
          User Identity: <code style={{ color: 'var(--accent-primary)' }}>default_user</code>
        </p>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => {
            localStorage.clear();
            window.location.reload();
          }}
          style={{ color: 'var(--status-danger)' }}
        >
          <TrashIcon size={14} />
          <span>Clear Local Client Cache</span>
        </button>
      </div>
    </div>
  );
};
