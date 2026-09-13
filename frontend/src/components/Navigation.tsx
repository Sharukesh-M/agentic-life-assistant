import React, { useState } from 'react';
import {
  DashboardIcon,
  ChatIcon,
  GoalsIcon,
  TasksIcon,
  InsightsIcon,
  VoiceIcon,
  MemoryIcon,
  SettingsIcon,
  SunIcon,
  MoonIcon,
} from './Icons';

interface TopbarProps {
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
  backendOnline: boolean;
}

export const Topbar: React.FC<TopbarProps> = ({ theme, setTheme, backendOnline }) => {
  return (
    <header className="topbar" role="banner">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
        <span style={{ fontSize: '1.1rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
          JARVIX
        </span>
        <span className="badge badge-neutral" style={{ fontSize: '0.65rem' }}>OS Agent v1.0</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* Connection Status Telemetry Indicator */}
        <div
          title={backendOnline ? "FastAPI Backend Online" : "Backend Offline / Mock Mode"}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.375rem',
            fontSize: '0.75rem',
            color: backendOnline ? 'var(--status-success)' : 'var(--status-warning)',
            padding: '0.25rem 0.625rem',
            borderRadius: 'var(--radius-sm)',
            background: backendOnline ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.08)',
            border: `1px solid ${backendOnline ? 'rgba(16, 185, 129, 0.25)' : 'rgba(245, 158, 11, 0.25)'}`,
          }}
        >
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: backendOnline ? 'var(--status-success)' : 'var(--status-warning)',
          }} />
          <span>{backendOnline ? 'System Connected' : 'Offline Mode'}</span>
        </div>

        {/* Theme Switcher */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <SunIcon size={14} /> : <MoonIcon size={14} />}
          <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
        </button>
      </div>
    </header>
  );
};

interface SidebarNavProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  unreadNotificationsCount: number;
}

export const SidebarNav: React.FC<SidebarNavProps> = ({
  activeTab,
  setActiveTab,
  unreadNotificationsCount,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', Icon: DashboardIcon },
    { id: 'chat', label: 'Chat Agent', Icon: ChatIcon },
    { id: 'goals', label: 'Goals & Strategy', Icon: GoalsIcon },
    { id: 'tasks', label: 'Action Items', Icon: TasksIcon },
    { id: 'notifications', label: 'Proactive Insights', Icon: InsightsIcon, badge: unreadNotificationsCount },
    { id: 'voice', label: 'OmniVoice', Icon: VoiceIcon },
    { id: 'memory', label: 'Preferences', Icon: MemoryIcon },
    { id: 'settings', label: 'Settings & Status', Icon: SettingsIcon },
  ];

  return (
    <nav className="sidebar-nav" aria-label="Main Navigation">
      <div style={{ padding: '0 0.5rem 0.75rem 0.5rem', fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Navigation
      </div>

      {navItems.map((item) => {
        const isActive = activeTab === item.id;
        const Icon = item.Icon;

        return (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            aria-current={isActive ? 'page' : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              width: '100%',
              padding: '0.625rem 0.875rem',
              borderRadius: 'var(--radius-md)',
              backgroundColor: isActive ? 'var(--accent-bg-subtle)' : 'transparent',
              color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
              border: isActive ? '1px solid var(--border-active)' : '1px solid transparent',
              fontWeight: isActive ? 600 : 400,
              fontSize: '0.84375rem',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'all var(--transition-fast)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Icon size={16} color={isActive ? 'var(--accent-primary)' : 'var(--text-muted)'} />
              <span>{item.label}</span>
            </div>

            {item.badge && item.badge > 0 ? (
              <span className="badge badge-danger" style={{ fontSize: '0.65rem', padding: '0.1rem 0.35rem' }}>
                {item.badge}
              </span>
            ) : null}
          </button>
        );
      })}
    </nav>
  );
};
