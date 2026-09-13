import React, { useEffect, useRef, useState } from 'react';
import { AlertIcon, CloseIcon } from './Icons';

interface ConfirmationModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  actionName?: string;
  isDestructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  title,
  message,
  actionName = 'Execute Action',
  isDestructive = false,
  onConfirm,
  onCancel,
}) => {
  const [confirmInput, setConfirmInput] = useState('');
  const confirmButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (isOpen) {
      setConfirmInput('');
      confirmButtonRef.current?.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const requiresTypeConfirm = isDestructive;
  const isConfirmDisabled = requiresTypeConfirm && confirmInput.trim().toUpperCase() !== 'CONFIRM';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-describedby="modal-desc"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(7, 10, 18, 0.75)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1.5rem',
      }}
    >
      <div
        className="surface-card"
        style={{
          maxWidth: '460px',
          width: '100%',
          backgroundColor: 'var(--bg-surface)',
          border: `1px solid ${isDestructive ? 'rgba(244, 63, 94, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`,
          boxShadow: 'var(--shadow-md)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <AlertIcon size={20} color={isDestructive ? 'var(--status-danger)' : 'var(--status-warning)'} />
            <div>
              <h3 id="modal-title" style={{ fontSize: '1.1rem', color: isDestructive ? 'var(--status-danger)' : 'var(--status-warning)' }}>
                {title}
              </h3>
              <span className="badge badge-warning" style={{ marginTop: '0.25rem', fontSize: '0.65rem' }}>
                Safety Gate Authorization Required
              </span>
            </div>
          </div>
          <button
            onClick={onCancel}
            aria-label="Close dialog"
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <CloseIcon size={16} />
          </button>
        </div>

        <p id="modal-desc" style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: '1.5' }}>
          {message}
        </p>

        {requiresTypeConfirm && (
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.375rem' }}>
              Type <strong>CONFIRM</strong> to authorize:
            </label>
            <input
              className="input-field"
              value={confirmInput}
              onChange={(e) => setConfirmInput(e.target.value)}
              placeholder="CONFIRM"
            />
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>
          <button
            ref={confirmButtonRef}
            className={`btn ${isDestructive ? 'btn-danger' : 'btn-primary'} btn-sm`}
            onClick={onConfirm}
            type="button"
            disabled={isConfirmDisabled}
          >
            {actionName}
          </button>
        </div>
      </div>
    </div>
  );
};
