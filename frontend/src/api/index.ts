import { Goal, Task, MemoryPreference, NotificationItem, ChatMessage, VoiceStatus } from '../types/api';

const API_BASE = '/api';
const DEFAULT_USER_ID = 'default_user';

export async function fetchJson<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const errorText = await response.text();
    let message = `API Error ${response.status}: ${response.statusText}`;
    try {
      const parsed = JSON.parse(errorText);
      if (parsed.detail) message = parsed.detail;
    } catch {
      if (errorText) message = errorText;
    }
    throw new Error(message);
  }

  return response.json();
}

// Health Check
export async function checkBackendHealth(): Promise<{ status: string; database?: string }> {
  try {
    const res = await fetch('/health');
    if (!res.ok) return { status: 'unhealthy' };
    return res.json();
  } catch (err) {
    return { status: 'offline' };
  }
}

// Chat API
export async function sendChatMessage(message: string, userId: string = DEFAULT_USER_ID): Promise<ChatMessage> {
  const data = await fetchJson<any>(`${API_BASE}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message, user_id: userId }),
  });

  return {
    id: data.id || `msg-${Date.now()}`,
    sender: 'assistant',
    content: data.response || data.message || 'No response generated.',
    timestamp: new Date().toISOString(),
    agent_trace: {
      intent: data.intent || data.classification,
      goal_correlation: data.goal_correlation,
      steps_executed: data.steps_executed || [],
      plan: data.plan,
      confirmation_required: data.confirmation_required,
      confirmation_action: data.confirmation_action,
    },
  };
}

// Goals API
export async function getGoals(userId: string = DEFAULT_USER_ID): Promise<Goal[]> {
  try {
    return await fetchJson<Goal[]>(`${API_BASE}/goals?user_id=${userId}`);
  } catch {
    return [];
  }
}

export async function createGoal(goal: Partial<Goal>, userId: string = DEFAULT_USER_ID): Promise<Goal> {
  return fetchJson<Goal>(`${API_BASE}/goals`, {
    method: 'POST',
    body: JSON.stringify({ ...goal, user_id: userId }),
  });
}

export async function deleteGoal(goalId: string): Promise<void> {
  await fetchJson(`${API_BASE}/goals/${goalId}`, { method: 'DELETE' });
}

// Tasks API
export async function getTasks(userId: string = DEFAULT_USER_ID): Promise<Task[]> {
  try {
    return await fetchJson<Task[]>(`${API_BASE}/tasks?user_id=${userId}`);
  } catch {
    return [];
  }
}

export async function createTask(task: Partial<Task>, userId: string = DEFAULT_USER_ID): Promise<Task> {
  return fetchJson<Task>(`${API_BASE}/tasks`, {
    method: 'POST',
    body: JSON.stringify({ ...task, user_id: userId }),
  });
}

export async function updateTaskStatus(taskId: string, status: string, notes?: string): Promise<Task> {
  return fetchJson<Task>(`${API_BASE}/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status, honest_verification_notes: notes }),
  });
}

// Memory API
export async function getMemoryPreferences(userId: string = DEFAULT_USER_ID): Promise<MemoryPreference[]> {
  try {
    return await fetchJson<MemoryPreference[]>(`${API_BASE}/memory/preferences?user_id=${userId}`);
  } catch {
    return [];
  }
}

export async function saveMemoryPreference(key: string, value: string, category: string = 'general', userId: string = DEFAULT_USER_ID): Promise<MemoryPreference> {
  return fetchJson<MemoryPreference>(`${API_BASE}/memory/preferences`, {
    method: 'POST',
    body: JSON.stringify({ key, value, category, user_id: userId }),
  });
}

export async function deleteMemoryPreference(key: string, userId: string = DEFAULT_USER_ID): Promise<void> {
  await fetchJson(`${API_BASE}/memory/preferences/${key}?user_id=${userId}`, { method: 'DELETE' });
}

// Notifications API
export async function getNotifications(userId: string = DEFAULT_USER_ID): Promise<NotificationItem[]> {
  try {
    return await fetchJson<NotificationItem[]>(`${API_BASE}/notifications?user_id=${userId}`);
  } catch {
    return [];
  }
}

export async function markNotificationRead(id: string): Promise<void> {
  await fetchJson(`${API_BASE}/notifications/${id}/read`, { method: 'POST' });
}

export async function dismissNotification(id: string): Promise<void> {
  await fetchJson(`${API_BASE}/notifications/${id}/dismiss`, { method: 'POST' });
}

// Voice API
export async function getVoiceStatus(): Promise<VoiceStatus> {
  try {
    return await fetchJson<VoiceStatus>(`${API_BASE}/voice/status`);
  } catch {
    return { stt_available: false, tts_available: false, active_voice: 'System Default (Mock)' };
  }
}

export async function synthesizeTTS(text: string): Promise<{ audio_url?: string; text: string }> {
  return fetchJson(`${API_BASE}/voice/tts`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}
