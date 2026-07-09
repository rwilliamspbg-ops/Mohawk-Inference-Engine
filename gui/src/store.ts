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
  error: string | null;
  setLoading: (loading: boolean) => void;
  setStreaming: (streaming: boolean) => void;
  setError: (error: string | null) => void;
  
  // Inference
  sendInferenceRequest: (messages: Message[]) => Promise<Message>;
  sendInferenceRequestStream: (messages: Message[], onToken: (token: string) => void) => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Models
  models: [],
  selectedModel: null,
  error: null,
  
  fetchModels: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/v1/models`);
      if (!response.ok) throw new Error('Failed to fetch models');
      const data = await response.json();

      const models: Model[] = data.data.map((m: any) => ({
        id: m.id,
        name: m.name || m.id,
        description: `${m.parameters || 'Unknown'} parameters`,
        parameters: m.parameters || 0,
        quantization: m.quantization || 'unknown',
        size: `${m.size_gb || 'Unknown'} GB`,
        status: m.loaded ? 'loaded' as const : 'unloaded' as const,
      }));
      
      set({ models, error: null });
    } catch (error) {
      console.error('Error fetching models:', error);
      set({ 
        error: 'Failed to connect to server. Make sure Mohawk server is running.',
        models: [
          { id: 'llama-3.2-3b-instruct', name: 'Llama 3.2 3B Instruct', description: '3B parameters, Q4_K_M', parameters: 3000000000, quantization: 'Q4_K_M', size: '2.1 GB', status: 'unloaded' as const },
          { id: 'mistral-7b-v0.3', name: 'Mistral 7B v0.3', description: '7B parameters, Q5_K_M', parameters: 7000000000, quantization: 'Q5_K_M', size: '4.5 GB', status: 'unloaded' as const },
          { id: 'phi-3-mini', name: 'Phi-3 Mini', description: '3.8B parameters, Q4_K_M', parameters: 3800000000, quantization: 'Q4_K_M', size: '2.4 GB', status: 'unloaded' as const },
        ]
      });
    }
  },
  
  setModels: (models) => set({ models }),
  setSelectedModel: (model) => set({ selectedModel: model }),
  
  loadModel: async (modelId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/v1/models/${modelId}/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || 'Failed to load model');
      }
      
      set((state) => ({
        models: state.models.map(m => 
          m.id === modelId ? { ...m, status: 'loaded' as const } : m
        ),
        selectedModel: state.models.find(m => m.id === modelId) || null,
        isLoading: false,
      }));
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error instanceof Error ? error.message : 'Failed to load model' 
      });
      throw error;
    }
  },
  
  unloadModel: async (modelId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/v1/models/${modelId}/unload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (!response.ok) throw new Error('Failed to unload model');
      
      set((state) => ({
        models: state.models.map(m => 
          m.id === modelId ? { ...m, status: 'unloaded' as const } : m
        ),
        selectedModel: state.selectedModel?.id === modelId ? null : state.selectedModel,
        isLoading: false,
      }));
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error instanceof Error ? error.message : 'Failed to unload model' 
      });
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
  
  // Inference - Non-streaming
  sendInferenceRequest: async (messages: Message[]) => {
    const state = get();
    const { selectedModel, settings } = state;
    
    if (!selectedModel) {
      throw new Error('No model selected');
    }
    
    set({ isLoading: true, error: null });
    
    try {
      const response = await fetch(`${API_BASE_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModel.id,
          messages: messages.map(m => ({ role: m.role, content: m.content })),
          temperature: settings.temperature,
          top_p: settings.topP,
          top_k: settings.topK,
          max_tokens: settings.maxTokens,
          stream: false,
        }),
      });
      
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || 'Inference request failed');
      }
      
      const data = await response.json();
      const choice = data.choices[0];
      
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: choice.message.content,
        timestamp: new Date(),
      };
      
      set({ isLoading: false });
      return assistantMessage;
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error instanceof Error ? error.message : 'Inference request failed' 
      });
      throw error;
    }
  },
  
  // Inference - Streaming
  sendInferenceRequestStream: async (messages: Message[], onToken: (token: string) => void) => {
    const state = get();
    const { selectedModel, settings } = state;
    
    if (!selectedModel) {
      throw new Error('No model selected');
    }
    
    set({ isStreaming: true, error: null });
    
    try {
      const response = await fetch(`${API_BASE_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModel.id,
          messages: messages.map(m => ({ role: m.role, content: m.content })),
          temperature: settings.temperature,
          top_p: settings.topP,
          top_k: settings.topK,
          max_tokens: settings.maxTokens,
          stream: true,
        }),
      });
      
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || 'Streaming request failed');
      }
      
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }
      
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              set({ isStreaming: false });
              return;
            }
            try {
              const parsed = JSON.parse(data);
              const choice = parsed.choices[0];
              const token = choice.delta?.content || '';
              if (token) {
                onToken(token);
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
      
      set({ isStreaming: false });
    } catch (error) {
      set({ 
        isStreaming: false, 
        error: error instanceof Error ? error.message : 'Streaming request failed' 
      });
      throw error;
    }
  },
}));
