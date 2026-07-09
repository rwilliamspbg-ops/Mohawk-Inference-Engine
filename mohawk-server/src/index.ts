import express, { Request, Response } from 'express';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';
import WebSocket, { WebSocketServer } from 'ws';
import winston from 'winston';
import http from 'http';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

// Types
interface ModelConfig {
  id: string;
  name: string;
  path: string;
  context_length: number;
  embedding: boolean;
  system_prompt: string;
  hardware_config: {
    n_gpu_layers: number;
    main_gpu: number;
    tensor_split: number[];
    offload_kqv: boolean;
    flash_attn: boolean;
  };
}

interface MCPConfig {
  version: string;
  engine: {
    name: string;
    max_concurrent_requests: number;
    default_backend: string;
  };
  models: ModelConfig[];
  system_prompts: Record<string, string>;
  metrics: {
    enabled: boolean;
    refresh_rate_ms: number;
    expose_hardware: boolean;
    log_level: string;
  };
  security: {
    api_keys: string[];
    cors_origins: string[];
  };
}

interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface InferenceRequest {
  model: string;
  messages: Message[];
  temperature?: number;
  top_p?: number;
  top_k?: number;
  max_tokens?: number;
  stream?: boolean;
  stop?: string[];
  system_prompt?: string;
}

interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

interface DeviceMetrics {
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

interface LiveMetrics {
  timestamp: number;
  requests_per_second: number;
  avg_latency_ms: number;
  tokens_per_second: number;
  active_connections: number;
  queue_depth: number;
  devices: DeviceMetrics[];
}

// Logger setup
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

// Load MCP configuration
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class MohawkEngine {
  private config: MCPConfig | null = null;
  private loadedModels: Map<string, any> = new Map();
  private metrics: LiveMetrics = {
    timestamp: Date.now(),
    requests_per_second: 0,
    avg_latency_ms: 0,
    tokens_per_second: 0,
    active_connections: 0,
    queue_depth: 0,
    devices: []
  };
  private requestQueue: Array<{
    request: InferenceRequest;
    resolve: (result: any) => void;
    reject: (error: Error) => void;
  }> = [];
  private processing = false;

  async loadConfig(): Promise<void> {
    try {
      const mcpPath = path.join(__dirname, '../mcp.json');
      const configData = await fs.readFile(mcpPath, 'utf-8');
      this.config = JSON.parse(configData);
      logger.info('MCP configuration loaded successfully', { 
        models: this.config?.models.length || 0,
        engine: this.config?.engine.name || 'unknown' 
      });
    } catch (error) {
      logger.error('Failed to load MCP configuration', { error });
      // Create default config
      this.config = this.getDefaultConfig();
    }
  }

  public getConfig(): MCPConfig | null {
    return this.config;
  }

  private getDefaultConfig(): MCPConfig {
    return {
      version: "1.0.0",
      engine: {
        name: "Mohawk-Inference-Engine",
        max_concurrent_requests: 10,
        default_backend: "llama-cpp"
      },
      models: [],
      system_prompts: {
        default: "You are a helpful AI assistant."
      },
      metrics: {
        enabled: true,
        refresh_rate_ms: 500,
        expose_hardware: true,
        log_level: "info"
      },
      security: {
        api_keys: [],
        cors_origins: ["*"]
      }
    };
  }

  async loadModel(modelId: string): Promise<boolean> {
    if (!this.config) {
      throw new Error('Configuration not loaded');
    }

    const modelConfig = this.config.models.find(m => m.id === modelId);
    if (!modelConfig) {
      throw new Error(`Model ${modelId} not found in configuration`);
    }

    // Check if already loaded
    if (this.loadedModels.has(modelId)) {
      logger.info('Model already loaded', { modelId });
      return true;
    }

    // Simulate model loading (replace with actual llama.cpp integration)
    logger.info('Loading model', { 
      modelId, 
      path: modelConfig.path,
      gpuLayers: modelConfig.hardware_config.n_gpu_layers 
    });

    // Placeholder for actual model loading
    const mockModel = {
      id: modelId,
      config: modelConfig,
      loaded: true,
      loadTime: Date.now()
    };

    this.loadedModels.set(modelId, mockModel);
    logger.info('Model loaded successfully', { modelId });
    
    // Update device metrics
    this.updateDeviceMetrics(modelConfig);
    
    return true;
  }

  private updateDeviceMetrics(modelConfig: ModelConfig): void {
    if (!this.config?.metrics.expose_hardware) return;

    // Simulate device metrics (replace with actual GPU monitoring)
    this.metrics.devices = [{
      device_id: modelConfig.hardware_config.main_gpu,
      device_name: 'NVIDIA GPU (Simulated)',
      memory_used_mb: 4096,
      memory_total_mb: 8192,
      utilization_percent: 75,
      temperature_celsius: 65,
      power_watts: 150,
      layers_offloaded: modelConfig.hardware_config.n_gpu_layers,
      total_layers: 32
    }];
  }

  async unloadModel(modelId: string): Promise<boolean> {
    if (!this.loadedModels.has(modelId)) {
      return false;
    }

    this.loadedModels.delete(modelId);
    logger.info('Model unloaded', { modelId });
    
    // Clear device metrics
    this.metrics.devices = [];
    
    return true;
  }

  getLoadedModels(): string[] {
    return Array.from(this.loadedModels.keys());
  }

  getModelConfig(modelId: string): ModelConfig | undefined {
    return this.config?.models.find(m => m.id === modelId);
  }

  async generate(request: InferenceRequest): Promise<{
    id: string;
    model: string;
    choices: Array<{
      index: number;
      message: Message;
      finish_reason: string;
    }>;
    usage: TokenUsage;
  }> {
    const startTime = Date.now();
    const requestId = uuidv4();

    logger.info('Processing inference request', { 
      requestId, 
      model: request.model,
      messages: request.messages.length 
    });

    // Validate model is loaded
    if (!this.loadedModels.has(request.model)) {
      await this.loadModel(request.model);
    }

    // Get system prompt
    let systemPrompt = request.system_prompt;
    if (!systemPrompt && this.config) {
      systemPrompt = this.config.system_prompts.default;
    }

    // Build prompt
    const fullMessages: Message[] = [];
    if (systemPrompt) {
      fullMessages.push({ role: 'system', content: systemPrompt });
    }
    fullMessages.push(...request.messages);

    // Simulate inference (replace with actual model inference)
    const responseText = this.simulateInference(fullMessages, request);
    
    const latency = Date.now() - startTime;
    const promptTokens = fullMessages.reduce((acc, msg) => acc + Math.ceil(msg.content.length / 4), 0);
    const completionTokens = Math.ceil(responseText.length / 4);

    // Update metrics
    this.metrics.requests_per_second = 1000 / latency;
    this.metrics.avg_latency_ms = latency;
    this.metrics.tokens_per_second = (completionTokens / latency) * 1000;

    logger.info('Inference completed', { 
      requestId, 
      latency,
      tokensPerSecond: this.metrics.tokens_per_second 
    });

    return {
      id: requestId,
      model: request.model,
      choices: [{
        index: 0,
        message: { role: 'assistant', content: responseText },
        finish_reason: 'stop'
      }],
      usage: {
        prompt_tokens: promptTokens,
        completion_tokens: completionTokens,
        total_tokens: promptTokens + completionTokens
      }
    };
  }

  private simulateInference(messages: Message[], request: InferenceRequest): string {
    // Placeholder for actual inference logic
    const lastMessage = messages[messages.length - 1];
    const responses = [
      `I understand you're asking about "${lastMessage.content.substring(0, 50)}...". Let me provide a comprehensive answer.`,
      `That's an interesting question! Based on my training, I can tell you that this requires careful consideration of multiple factors.`,
      `Here's what I know about this topic: The key aspects involve understanding the underlying principles and applying them systematically.`
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  }

  async *generateStream(request: InferenceRequest): AsyncGenerator<{
    token: string;
    finish_reason?: string;
  }> {
    const requestId = uuidv4();
    logger.info('Starting streaming inference', { requestId, model: request.model });

    // Validate model is loaded
    if (!this.loadedModels.has(request.model)) {
      await this.loadModel(request.model);
    }

    // Simulate streaming tokens
    const responseText = this.simulateInference(request.messages, request);
    const tokens = responseText.split(' ');

    for (let i = 0; i < tokens.length; i++) {
      yield {
        token: tokens[i] + (i < tokens.length - 1 ? ' ' : ''),
        finish_reason: i === tokens.length - 1 ? 'stop' : undefined
      };
      
      // Simulate token generation delay
      await new Promise(resolve => setTimeout(resolve, 50));
    }

    logger.info('Streaming inference completed', { requestId });
  }

  getLiveMetrics(): LiveMetrics {
    this.metrics.timestamp = Date.now();
    this.metrics.active_connections = this.requestQueue.length;
    this.metrics.queue_depth = this.requestQueue.length;
    return { ...this.metrics };
  }
}

// Initialize engine
const engine = new MohawkEngine();
await engine.loadConfig();

// Express app setup
const app = express();
const engineConfig = engine.getConfig();
app.use(cors({
  origin: engineConfig?.security.cors_origins || '*',
  credentials: true
}));
app.use(express.json());

// API Key middleware
const authenticateApiKey = (req: Request, res: Response, next: Function) => {
  const apiKey = req.headers['authorization']?.replace('Bearer ', '');
  
  if (!engineConfig?.security.api_keys.length) {
    return next(); // No keys configured, allow all
  }

  if (apiKey && engineConfig.security.api_keys.includes(apiKey)) {
    return next();
  }

  res.status(401).json({ error: 'Invalid or missing API key' });
};

app.use(authenticateApiKey);

// Health check
app.get('/health', (req: Request, res: Response) => {
  res.json({ 
    status: 'healthy',
    uptime: process.uptime(),
    timestamp: Date.now()
  });
});

// Models endpoint
app.get('/v1/models', (req: Request, res: Response) => {
  const models = engineConfig?.models.map(m => ({
    id: m.id,
    object: 'model',
    created: Date.now(),
    owned_by: 'mohawk',
    permission: [],
    root: m.id,
    parent: null
  })) || [];

  res.json({ object: 'list', data: models });
});

// Load model
app.post('/v1/models/:modelId/load', async (req: Request, res: Response) => {
  try {
    const { modelId } = req.params;
    const success = await engine.loadModel(modelId);
    res.json({ success, model: modelId, status: 'loaded' });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Unload model
app.post('/v1/models/:modelId/unload', async (req: Request, res: Response) => {
  try {
    const { modelId } = req.params;
    const success = await engine.unloadModel(modelId);
    res.json({ success, model: modelId, status: success ? 'unloaded' : 'not_found' });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Chat completions (OpenAI compatible)
app.post('/v1/chat/completions', async (req: Request, res: Response) => {
  try {
    const body: InferenceRequest = req.body;
    
    if (body.stream) {
      // Streaming response
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');

      for await (const chunk of engine.generateStream(body)) {
        const data = {
          id: uuidv4(),
          object: 'chat.completion.chunk',
          created: Date.now(),
          model: body.model,
          choices: [{
            index: 0,
            delta: { content: chunk.token },
            finish_reason: chunk.finish_reason || null
          }]
        };
        res.write(`data: ${JSON.stringify(data)}\n\n`);
      }
      res.write('data: [DONE]\n\n');
      res.end();
    } else {
      // Standard response
      const result = await engine.generate(body);
      res.json(result);
    }
  } catch (error: any) {
    logger.error('Chat completion error', { error });
    res.status(500).json({ error: error.message });
  }
});

// Metrics endpoint
app.get('/v1/metrics', (req: Request, res: Response) => {
  const metrics = engine.getLiveMetrics();
  res.json(metrics);
});

// Device metrics endpoint
app.get('/v1/metrics/devices', (req: Request, res: Response) => {
  const metrics = engine.getLiveMetrics();
  res.json({ devices: metrics.devices });
});

// System prompts endpoint
app.get('/v1/system-prompts', (req: Request, res: Response) => {
  res.json(engineConfig?.system_prompts || {});
});

// Create HTTP server
const server = http.createServer(app);

// WebSocket server for real-time metrics
const wss = new WebSocketServer({ server, path: '/ws/metrics' });

wss.on('connection', (ws: WebSocket) => {
  logger.info('WebSocket client connected');
  
  const metricsInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(engine.getLiveMetrics()));
    }
  }, engineConfig?.metrics.refresh_rate_ms || 500);

  ws.on('close', () => {
    clearInterval(metricsInterval);
    logger.info('WebSocket client disconnected');
  });
});

// Start server
const PORT = process.env.PORT || 8080;
server.listen(PORT, () => {
  logger.info(`Mohawk Inference Engine running on port ${PORT}`);
  logger.info('Available endpoints:', {
    health: `http://localhost:${PORT}/health`,
    models: `http://localhost:${PORT}/v1/models`,
    chat: `http://localhost:${PORT}/v1/chat/completions`,
    metrics: `http://localhost:${PORT}/v1/metrics`,
    websocket: `ws://localhost:${PORT}/ws/metrics`
  });
});

export default app;
