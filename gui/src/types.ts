export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface Model {
  id: string;
  name: string;
  description: string;
  parameters: string;
  quantization: string;
  size: string;
  status: 'loaded' | 'unloaded' | 'loading';
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  modelId: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface InferenceSettings {
  temperature: number;
  topP: number;
  topK: number;
  maxTokens: number;
  stopSequences: string[];
  systemPrompt: string;
}

export interface StreamToken {
  token: string;
  finishReason?: 'stop' | 'length' | null;
}

export interface InferenceResponse {
  id: string;
  model: string;
  choices: {
    index: number;
    message: Message;
    finishReason: string;
  }[];
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}
