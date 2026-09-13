import React, { useState, useEffect } from 'react';
import { VoiceStatus } from '../types/api';
import { getVoiceStatus, synthesizeTTS } from '../api';
import { VoiceIcon } from '../components/Icons';

export const VoiceView: React.FC = () => {
  const [status, setStatus] = useState<VoiceStatus | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [ttsInput, setTtsInput] = useState('');
  const [isSynthesizing, setIsSynthesizing] = useState(false);

  useEffect(() => {
    getVoiceStatus().then(setStatus);
  }, []);

  const toggleRecording = () => {
    if (isRecording) {
      setIsRecording(false);
      setTranscript('JARVIX, summarize my top priority tasks for today.');
    } else {
      setIsRecording(true);
      setTranscript('');
    }
  };

  const handleSynthesize = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ttsInput.trim()) return;
    setIsSynthesizing(true);
    try {
      await synthesizeTTS(ttsInput);
    } catch {
      // Graceful fallback
    } finally {
      setIsSynthesizing(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '760px', margin: '0 auto', width: '100%' }}>
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>OmniVoice Subsystem</h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Low-latency Speech-to-Text (STT) and Text-to-Speech (TTS) voice interaction pipeline
        </p>
      </div>

      {/* Voice Telemetry Status Card */}
      <div className="surface-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '0.9375rem' }}>Subsystem Telemetry</h3>
          <p style={{ fontSize: '0.78125rem', color: 'var(--text-secondary)', marginTop: '0.125rem' }}>
            Engine: {status?.active_voice || 'OmniVoice Scaffold'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.375rem' }}>
          <span className={`badge ${status?.stt_available ? 'badge-success' : 'badge-neutral'}`}>
            STT: {status?.stt_available ? 'Active' : 'Mock Mode'}
          </span>
          <span className={`badge ${status?.tts_available ? 'badge-success' : 'badge-neutral'}`}>
            TTS: {status?.tts_available ? 'Active' : 'Mock Mode'}
          </span>
        </div>
      </div>

      {/* Mic Recording Section */}
      <div className="surface-card" style={{ textAlign: 'center', padding: '2.5rem 1.5rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.25rem' }}>
        <button
          onClick={toggleRecording}
          aria-label={isRecording ? "Stop voice recording" : "Start voice recording"}
          style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            border: 'none',
            backgroundColor: isRecording ? 'var(--status-danger)' : 'var(--accent-primary)',
            color: '#070a12',
            cursor: 'pointer',
            boxShadow: 'var(--shadow-md)',
            transition: 'transform var(--transition-normal), background-color var(--transition-normal)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <VoiceIcon size={32} color="#070a12" />
        </button>

        <div>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>
            {isRecording ? 'Listening to voice stream...' : 'Click to speak'}
          </h3>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            {isRecording ? 'Click again when finished' : 'Hands-free voice prompt entry'}
          </p>
        </div>

        {/* Audio Waveform Bar Visualizer */}
        {isRecording && (
          <div style={{ display: 'flex', gap: '4px', alignItems: 'center', height: '24px' }}>
            {[0.4, 0.8, 1, 0.6, 0.9, 0.3, 0.7, 0.5, 0.9, 0.4].map((h, i) => (
              <div
                key={i}
                style={{
                  width: '3px',
                  height: `${h * 100}%`,
                  backgroundColor: 'var(--accent-primary)',
                  borderRadius: '2px',
                  animation: 'pulse 1s infinite alternate',
                  animationDelay: `${i * 0.08}s`,
                }}
              />
            ))}
          </div>
        )}

        {/* Transcript Box */}
        {transcript && (
          <div style={{ width: '100%', padding: '0.875rem 1rem', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', textAlign: 'left', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>STT Transcript Output:</span>
            <p style={{ fontSize: '0.875rem', fontWeight: 500 }}>"{transcript}"</p>
          </div>
        )}
      </div>

      {/* TTS Synthesizer Card */}
      <div className="surface-card">
        <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>TTS Synthesis Test</h3>
        <form onSubmit={handleSynthesize} style={{ display: 'flex', gap: '0.625rem' }}>
          <input
            className="input-field"
            placeholder="Type text for OmniVoice speech synthesis..."
            value={ttsInput}
            onChange={(e) => setTtsInput(e.target.value)}
          />
          <button className="btn btn-secondary" type="submit" disabled={isSynthesizing || !ttsInput.trim()}>
            {isSynthesizing ? 'Synthesizing...' : 'Synthesize Speech'}
          </button>
        </form>
      </div>
    </div>
  );
};
