import { create } from 'zustand';
import { Message, Model, ChatSession, InferenceSettings } from './types';

const API_BASE_URL = 'http://localhost:8080';

interface AppState {
  // Models
  models: Model[];
  selectedModel: Model | null;
  setModels: (models: Model[]) => void;
  setSelectedModel: (model: Model | null) => void;
  loadModel: (modelId: string) => Promise<void>;
  unloadModel: (modelId: string) => Promise<void>;
  fetchModels: () => Promise<void>;
  
  // Chat Sessions
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  setSessions: (sessions: ChatSession[]) => void;
  setCurrentSession: (session: ChatSession | null) => void;
  createSession: () => ChatSession;
  deleteSession: (sessionId: string) => void;
  addMessage: (sessionId: string, message: Message) => void;
  
  // Settings
  settings: InferenceSettings;
  updateSettings: (settings: Partial<InferenceSettings>) => void;
  
  // UI State
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;
  setLoading: (loading: boolean) => void;
  setStreaming: (streaming: boolean) => void;
  setError: (error: string | null) => void;
  
  // Inference
  sendInferenceRequest: (messages: Message[]) => Promise<Message>;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Models
  models: [],
  selectedModel: null,
  
  fetchModels: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/v1/models`);
      if (!response.ok) throw new Error('Failed to fetch models');
      const data = await response.json();
      
      const models: Model[] = data.data.map((m: any) => ({
        id: m.id,
        name: m.name,
        description: `${m.parameters} parameters, ${m.quantization} quantization`,
        parameters: m.parameters,
        quantization: m.quantization,
        size: `${m.size_gb} GB`,
        status: m.loaded ? 'loaded' as const : 'unloaded' as const,
      }));
      
      set({ models });
    } catch (error) {
      console.error('Error fetching models:', error);
      set({ error: 'Failed to connect to server. Make sure Mohawk server is running.' });
    }
  },
  
  setModels: (models) => set({ models }),
  setSelectedModel: (model) => set({ selectedModel: model }),
  
  loadModel: async (modelId) => {
    set({ isLoading: true });
    try {
      const response = await fetch(`${API_BASE_URL}/api/models/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: modelId }),
      });
      
      if (!response.ok) throw new Error('Failed to load model');
      
      set((state) => ({
        models: state.models.map(m => 
          m.id === modelId ? { ...m, status: 'loaded' as const } : m
        ),
        selectedModel: state.models.find(m => m.id === modelId) || null,
        isLoading: false,
      }));
    } catch (error) {
      set({ isLoading: false, error: 'Failed to load model' });
      throw error;
    }
  },
  
  unloadModel: async (modelId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/models/unload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: modelId }),
      });
      
      if (!response.ok) throw new Error('Failed to unload model');
      
      set((state) => ({
        models: state.models.map(m => 
          m.id === modelId ? { ...m, status: 'unloaded' as const } : m
        ),
        selectedModel: state.selectedModel?.id === modelId ? null : state.selectedModel,
      }));
    } catch (error) {
      set({ error: 'Failed to unload model' });
      throw error;
    }
  },
  
  // Chat Sessions
  sessions: [],
  currentSession: null,
  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (session) => set({ currentSession: session }),
  createSession: () => {
    const newSession: ChatSession = {
      id: crypto.randomUUID(),
      title: 'New Chat',
      messages: [],
      modelId: get().selectedModel?.id || '',
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    set((state) => ({
      sessions: [...state.sessions, newSession],
      currentSession: newSession,
    }));
    return newSession;
  },
  deleteSession: (sessionId) => {
    set((state) => ({
      sessions: state.sessions.filter(s => s.id !== sessionId),
      currentSession: state.currentSession?.id === sessionId ? null : state.currentSession,
    }));
  },
  addMessage: (sessionId, message) => {
    set((state) => ({
      sessions: state.sessions.map(s => 
        s.id === sessionId 
          ? { ...s, messages: [...s.messages, message], updatedAt: new Date() }
          : s
      ),
      currentSession: state.currentSession?.id === sessionId
        ? { ...state.currentSession, messages: [...state.currentSession.messages, message], updatedAt: new Date() }
        : state.currentSession,
    }));
  },
  
  // Settings
  settings: {
    temperature: 0.7,
    topP: 0.9,
    topK: 40,
    maxTokens: 2048,
    stopSequences: [],
    systemPrompt: 'You are a helpful AI assistant.',
  },
  updateSettings: (newSettings) => {
    set((state) => ({
      settings: { ...state.settings, ...newSettings },
    }));
  },
  
  // UI State
  isLoading: false,
  isStreaming: false,
  error: null,
  setLoading: (loading) => set({ isLoading: loading }),
  setStreaming: (streaming) => set({ isStreaming: streaming }),
  setError: (error) => set({ error }),
}));
