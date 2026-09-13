export type GoalStatus = 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'ABANDONED';
export type TaskStatus = 'CREATED' | 'IN_PROGRESS' | 'COMPLETED' | 'SKIPPED' | 'POSTPONED' | 'RESCHEDULED';
export type TaskPriority = 'HIGH' | 'MEDIUM' | 'LOW';
export type NotificationPriority = 'INFO' | 'RECOMMENDATION' | 'ACTION_REQUIRED';

export interface Milestone {
  id: string;
  title: string;
  description?: string;
  order: number;
  completed: boolean;
}

export interface Goal {
  id: string;
  user_id: string;
  title: string;
  description: string;
  category: string;
  status: GoalStatus;
  priority: TaskPriority;
  deadline?: string;
  progress: number;
  milestones: Milestone[];
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  user_id: string;
  goal_id?: string;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  due_date?: string;
  completed_at?: string;
  honest_verification_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface MemoryPreference {
  id: string;
  user_id: string;
  key: string;
  value: string;
  category: string;
  updated_at: string;
}

export interface NotificationItem {
  id: string;
  user_id: string;
  title: string;
  message: string;
  priority: NotificationPriority;
  category: string;
  related_goal_id?: string;
  read: boolean;
  dismissed: boolean;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
  agent_trace?: {
    intent?: string;
    goal_correlation?: string;
    steps_executed?: string[];
    plan?: any;
    confirmation_required?: boolean;
    confirmation_action?: string;
  };
}

export interface VoiceStatus {
  stt_available: boolean;
  tts_available: boolean;
  active_voice: string;
}
