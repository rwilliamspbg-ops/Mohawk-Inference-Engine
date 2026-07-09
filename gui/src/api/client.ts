import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';
const API_KEY = import.meta.env.VITE_API_KEY || 'mk_live_1234567890';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
  }
});

export interface Model {
  id: string;
  name?: string;
  object: string;
  created: number;
  owned_by: string;
}

export interface SystemPrompts {
  default: string;
  [key: string]: string;
}

export interface DeviceMetrics {
  device_id: number;
  device_name: string;
  memory_used_mb: number;
  memory_total_mb: number;
  utilization_percent: number;
  temperature_celsius: number;
  power_watts: number;
  layers_offloaded: number;
  total_layers: number;
}

export interface LiveMetrics {
  timestamp: number;
  requests_per_second: number;
  avg_latency_ms: number;
  tokens_per_second: number;
  active_connections: number;
  queue_depth: number;
  devices: DeviceMetrics[];
}

export class MohawkAPI {
  // Health check
  async health(): Promise<{ status: string; uptime: number; timestamp: number }> {
    const response = await apiClient.get('/health');
    return response.data;
  }

  // Get all available models
  async getModels(): Promise<Model[]> {
    const response = await apiClient.get('/v1/models');
    return response.data.data;
  }

  // Load a model
  async loadModel(modelId: string): Promise<{ success: boolean; model: string; status: string }> {
    const response = await apiClient.post(`/v1/models/${modelId}/load`);
    return response.data;
  }

  // Unload a model
  async unloadModel(modelId: string): Promise<{ success: boolean; model: string; status: string }> {
    const response = await apiClient.post(`/v1/models/${modelId}/unload`);
    return response.data;
  }

  // Get system prompts
  async getSystemPrompts(): Promise<SystemPrompts> {
    const response = await apiClient.get('/v1/system-prompts');
    return response.data;
  }

  // Get live metrics
  async getMetrics(): Promise<LiveMetrics> {
    const response = await apiClient.get('/v1/metrics');
    return response.data;
  }

  // Get device-specific metrics
  async getDeviceMetrics(): Promise<{ devices: DeviceMetrics[] }> {
    const response = await apiClient.get('/v1/metrics/devices');
    return response.data;
  }

  // Chat completion (non-streaming)
  async chatCompletion(params: {
    model: string;
    messages: Array<{ role: string; content: string }>;
    temperature?: number;
    top_p?: number;
    top_k?: number;
    max_tokens?: number;
    system_prompt?: string;
  }): Promise<{
    id: string;
    model: string;
    choices: Array<{
      index: number;
      message: { role: string; content: string };
      finish_reason: string;
    }>;
    usage: {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
    };
  }> {
    const response = await apiClient.post('/v1/chat/completions', {
      ...params,
      stream: false
    });
    return response.data;
  }

  // Chat completion with streaming
  async *chatCompletionStream(params: {
    model: string;
    messages: Array<{ role: string; content: string }>;
    temperature?: number;
    top_p?: number;
    top_k?: number;
    max_tokens?: number;
    system_prompt?: string;
  }): AsyncGenerator<{
    token: string;
    finish_reason?: string;
  }> {
    const response = await fetch(`${API_BASE_URL}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        ...params,
        stream: true
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
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
            return;
          }
          try {
            const parsed = JSON.parse(data);
            const choice = parsed.choices[0];
            yield {
              token: choice.delta?.content || '',
              finish_reason: choice.finish_reason || undefined
            };
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    }
  }

  // WebSocket connection for real-time metrics
  connectMetricsWebSocket(onMessage: (metrics: LiveMetrics) => void): WebSocket {
    const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws/metrics';
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const metrics = JSON.parse(event.data);
        onMessage(metrics);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    return ws;
  }
}

export const mohawkAPI = new MohawkAPI();
