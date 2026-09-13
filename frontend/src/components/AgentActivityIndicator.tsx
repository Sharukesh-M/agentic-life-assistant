import React, { useState } from 'react';
import { CheckIcon } from './Icons';

interface AgentActivityIndicatorProps {
  steps?: string[];
  intent?: string;
  isExecuting?: boolean;
}

export const AgentActivityIndicator: React.FC<AgentActivityIndicatorProps> = ({
  steps = [],
  intent,
  isExecuting = false,
}) => {
  const [expanded, setExpanded] = useState(false);

  const defaultSteps = [
    'Classifying Intent & Enforcing Safety Overlay',
    'Retrieving Tiered Memory & Active Goals',
    'Decomposing Plan & Scheduling Tools',
    'Verifying Execution & Formulating Response',
  ];

  const activeSteps = steps.length > 0 ? steps : defaultSteps;

  return (
    <div
      style={{
        padding: '0.625rem 0.875rem',
        borderRadius: 'var(--radius-md)',
        backgroundColor: 'var(--bg-surface-elevated)',
        border: '1px solid var(--border-color)',
        fontSize: '0.8125rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.375rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: isExecuting ? 'var(--cyan-400)' : 'var(--emerald-400)',
          }} />
          <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
            {isExecuting ? 'Agent executing...' : 'Agent Trace'}
          </span>
          {intent && (
            <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>
              Intent: {intent}
            </span>
          )}
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: '0.75rem',
          }}
        >
          {expanded ? 'Hide Steps ▲' : 'Show Steps ▼'}
        </button>
      </div>

      {(expanded || isExecuting) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginTop: '0.25rem', paddingTop: '0.375rem', borderTop: '1px solid var(--border-color)' }}>
          {activeSteps.map((step, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
              <CheckIcon size={12} color="var(--emerald-400)" />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.725rem' }}>{step}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
