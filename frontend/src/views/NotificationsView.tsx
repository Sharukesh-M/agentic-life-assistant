import React from 'react';
import { NotificationItem } from '../types/api';

interface NotificationsViewProps {
  notifications: NotificationItem[];
  onMarkRead: (id: string) => Promise<void>;
  onDismiss: (id: string) => Promise<void>;
}

export const NotificationsView: React.FC<NotificationsViewProps> = ({
  notifications,
  onMarkRead,
  onDismiss,
}) => {
  const activeNotifications = notifications.filter((n) => !n.dismissed);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Proactive Insights</h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Autonomous goal monitoring, task timeline checks, and system notifications
        </p>
      </div>

      {activeNotifications.length === 0 ? (
        <div className="surface-card" style={{ textAlign: 'center', padding: '3rem 1.5rem', color: 'var(--text-muted)' }}>
          <h3>No active insights</h3>
          <p style={{ fontSize: '0.8125rem', marginTop: '0.375rem' }}>
            JARVIX will surface notifications here when background goals or events require your review.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
          {activeNotifications.map((item) => {
            const isActionRequired = item.priority === 'ACTION_REQUIRED';
            const isRecommendation = item.priority === 'RECOMMENDATION';

            return (
              <div
                key={item.id}
                className="surface-card"
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  padding: '1.125rem',
                  gap: '1rem',
                  backgroundColor: item.read ? 'var(--bg-surface)' : 'var(--bg-surface-subtle)',
                  borderLeft: `3px solid ${
                    isActionRequired ? 'var(--status-danger)' : isRecommendation ? 'var(--warning-400)' : 'var(--cyan-400)'
                  }`,
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.375rem' }}>
                    <span className={`badge ${isActionRequired ? 'badge-danger' : isRecommendation ? 'badge-warning' : 'badge-info'}`}>
                      {item.priority}
                    </span>
                    {!item.read && <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>NEW</span>}
                    <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                      {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.25rem' }}>{item.title}</h3>
                  <p style={{ fontSize: '0.84375rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>{item.message}</p>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {!item.read && (
                    <button className="btn btn-secondary btn-sm" onClick={() => onMarkRead(item.id)}>
                      Mark Read
                    </button>
                  )}
                  <button className="btn btn-secondary btn-sm" onClick={() => onDismiss(item.id)}>
                    Dismiss
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
