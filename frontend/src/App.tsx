import React, { useState, useEffect } from 'react';
import { Topbar, SidebarNav } from './components/Navigation';
import { DashboardView } from './views/DashboardView';
import { ChatView } from './views/ChatView';
import { GoalsView } from './views/GoalsView';
import { TasksView } from './views/TasksView';
import { NotificationsView } from './views/NotificationsView';
import { VoiceView } from './views/VoiceView';
import { MemoryView } from './views/MemoryView';
import { SettingsView } from './views/SettingsView';

import {
  Goal,
  Task,
  MemoryPreference,
  NotificationItem,
  ChatMessage,
  TaskStatus,
} from './types/api';

import {
  checkBackendHealth,
  sendChatMessage,
  getGoals,
  createGoal,
  deleteGoal,
  getTasks,
  createTask,
  updateTaskStatus,
  getMemoryPreferences,
  saveMemoryPreference,
  deleteMemoryPreference,
  getNotifications,
  markNotificationRead,
  dismissNotification,
} from './api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [backendOnline, setBackendOnline] = useState<boolean>(false);

  // Data states
  const [goals, setGoals] = useState<Goal[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [memoryPrefs, setMemoryPrefs] = useState<MemoryPreference[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState<boolean>(false);

  // Apply theme attribute to html element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Initial load & data fetching
  const refreshAllData = async () => {
    const health = await checkBackendHealth();
    const isOnline = health.status !== 'offline';
    setBackendOnline(isOnline);

    if (isOnline) {
      try {
        const [g, t, m, n] = await Promise.all([
          getGoals(),
          getTasks(),
          getMemoryPreferences(),
          getNotifications(),
        ]);
        setGoals(g);
        setTasks(t);
        setMemoryPrefs(m);
        setNotifications(n);
      } catch (err) {
        console.warn('Backend endpoint fetch fallback', err);
      }
    }
  };

  useEffect(() => {
    refreshAllData();
    const interval = setInterval(refreshAllData, 15000);
    return () => clearInterval(interval);
  }, []);

  // Handlers
  const handleSendMessage = async (text: string) => {
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsChatLoading(true);

    try {
      const response = await sendChatMessage(text);
      setMessages((prev) => [...prev, response]);
      await refreshAllData();
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        content: `Error communicating with JARVIX agent: ${err.message || 'Offline'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleCreateGoal = async (goalData: Partial<Goal>) => {
    try {
      const newG = await createGoal(goalData);
      setGoals((prev) => [...prev, newG]);
    } catch {
      const mockG: Goal = {
        id: `g-${Date.now()}`,
        user_id: 'default_user',
        title: goalData.title || 'New Goal',
        description: goalData.description || '',
        category: goalData.category || 'General',
        status: 'ACTIVE',
        priority: goalData.priority || 'MEDIUM',
        progress: 0,
        milestones: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setGoals((prev) => [...prev, mockG]);
    }
  };

  const handleDeleteGoal = async (id: string) => {
    setGoals((prev) => prev.filter((g) => g.id !== id));
    try {
      await deleteGoal(id);
    } catch (e) {}
  };

  const handleCreateTask = async (taskData: Partial<Task>) => {
    try {
      const newT = await createTask(taskData);
      setTasks((prev) => [...prev, newT]);
    } catch {
      const mockT: Task = {
        id: `t-${Date.now()}`,
        user_id: 'default_user',
        title: taskData.title || 'New Task',
        description: taskData.description,
        status: 'CREATED',
        priority: taskData.priority || 'MEDIUM',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setTasks((prev) => [...prev, mockT]);
    }
  };

  const handleUpdateTaskStatus = async (id: string, status: TaskStatus, notes?: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status, honest_verification_notes: notes } : t))
    );
    try {
      await updateTaskStatus(id, status, notes);
    } catch (e) {}
  };

  const handleSaveMemoryPreference = async (key: string, value: string, category: string = 'general') => {
    try {
      const saved = await saveMemoryPreference(key, value, category);
      setMemoryPrefs((prev) => [...prev.filter((p) => p.key !== key), saved]);
    } catch {
      const mockP: MemoryPreference = {
        id: `m-${Date.now()}`,
        user_id: 'default_user',
        key,
        value,
        category,
        updated_at: new Date().toISOString(),
      };
      setMemoryPrefs((prev) => [...prev.filter((p) => p.key !== key), mockP]);
    }
  };

  const handleDeleteMemoryPreference = async (key: string) => {
    setMemoryPrefs((prev) => prev.filter((p) => p.key !== key));
    try {
      await deleteMemoryPreference(key);
    } catch (e) {}
  };

  const handleMarkNotificationRead = async (id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    try {
      await markNotificationRead(id);
    } catch (e) {}
  };

  const handleDismissNotification = async (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    try {
      await dismissNotification(id);
    } catch (e) {}
  };

  const unreadNotificationsCount = notifications.filter((n) => !n.read && !n.dismissed).length;

  return (
    <div className="app-container">
      {/* Top Header Spanning Full Width */}
      <Topbar
        theme={theme}
        setTheme={setTheme}
        backendOnline={backendOnline}
      />

      {/* App Body Container (Sidebar Left + Main Right) */}
      <div className="app-body">
        <SidebarNav
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          unreadNotificationsCount={unreadNotificationsCount}
        />

        <main className="main-content">
          <div className="page-wrapper">
            {activeTab === 'dashboard' && (
              <DashboardView
                goals={goals}
                tasks={tasks}
                notifications={notifications}
                onNavigate={setActiveTab}
                onSendQuickChat={handleSendMessage}
              />
            )}

            {activeTab === 'chat' && (
              <ChatView
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isChatLoading}
              />
            )}

            {activeTab === 'goals' && (
              <GoalsView
                goals={goals}
                onCreateGoal={handleCreateGoal}
                onDeleteGoal={handleDeleteGoal}
              />
            )}

            {activeTab === 'tasks' && (
              <TasksView
                tasks={tasks}
                onCreateTask={handleCreateTask}
                onUpdateTaskStatus={handleUpdateTaskStatus}
              />
            )}

            {activeTab === 'notifications' && (
              <NotificationsView
                notifications={notifications}
                onMarkRead={handleMarkNotificationRead}
                onDismiss={handleDismissNotification}
              />
            )}

            {activeTab === 'voice' && <VoiceView />}

            {activeTab === 'memory' && (
              <MemoryView
                preferences={memoryPrefs}
                onSavePreference={handleSaveMemoryPreference}
                onDeletePreference={handleDeleteMemoryPreference}
              />
            )}

            {activeTab === 'settings' && (
              <SettingsView
                theme={theme}
                setTheme={setTheme}
                backendOnline={backendOnline}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
};
