//! Core inference engine implementation with llama.cpp backend

use crate::error::{MohawkError, Result};
use crate::models::*;
use std::collections::HashMap;
use std::sync::Arc;
use std::path::PathBuf;
use tokio::sync::{Mutex, RwLock};
use tracing::{info, warn, debug, error};

/// Main inference engine managing models and generation
pub struct InferenceEngine {
    /// Loaded models (model_id -> model_data)
    models: Arc<RwLock<HashMap<String, ModelData>>>,
    /// Request statistics
    stats: Arc<Mutex<EngineStats>>,
    /// Default model ID
    default_model: Option<String>,
    /// Model storage path
    model_path: PathBuf,
}

struct ModelData {
    info: ModelInfo,
    status: ModelStatus,
    /// Actual llama.cpp model instance
    backend: Option<llama_cpp_2::Llama>,
}

#[derive(Default)]
struct EngineStats {
    requests_total: i64,
    tokens_generated: i64,
    start_time: std::time::Instant,
}

impl InferenceEngine {
    /// Create a new inference engine with custom model path
    pub fn new(model_path: Option<PathBuf>) -> Result<Self> {
        let path = model_path.unwrap_or_else(|| PathBuf::from("./models"));
        
        info!("Initializing Mohawk Inference Engine");
        info!("Model storage path: {:?}", path);
        
        // Create model directory if it doesn't exist
        if !path.exists() {
            std::fs::create_dir_all(&path)
                .map_err(|e| MohawkError::InternalError(format!("Failed to create model directory: {}", e)))?;
        }
        
        Ok(Self {
            models: Arc::new(RwLock::new(HashMap::new())),
            stats: Arc::new(Mutex::new(EngineStats::default())),
            default_model: None,
            model_path: path,
        })
    }
    
    /// Register a model for loading
    pub async fn register_model(&self, model_info: ModelInfo) -> Result<()> {
        let mut models = self.models.write().await;
        
        if models.contains_key(&model_info.id) {
            return Err(MohawkError::InvalidRequest(
                format!("Model {} already registered", model_info.id)
            ));
        }
        
        let model_data = ModelData {
            info: model_info.clone(),
            status: ModelStatus::Unloaded,
            backend: None,
        };
        
        models.insert(model_info.id.clone(), model_data);
        info!("Registered model: {}", model_info.id);
        
        Ok(())
    }
    
    /// Download a model from HuggingFace
    pub async fn download_model(&self, repo_id: &str, filename: &str) -> Result<PathBuf> {
        use reqwest::Client;
        use tokio::io::AsyncWriteExt;
        
        let url = format!("https://huggingface.co/{}/resolve/main/{}", repo_id, filename);
        info!("Downloading model from: {}", url);
        
        let client = Client::new();
        let response = client.get(&url).send().await
            .map_err(|e| MohawkError::InternalError(format!("Download failed: {}", e)))?;
        
        if !response.status().is_success() {
            return Err(MohawkError::InternalError(
                format!("Download failed with status: {}", response.status())
            ));
        }
        
        let total_size = response.content_length()
            .ok_or_else(|| MohawkError::InternalError("Unknown content length".to_string()))?;
        
        info!("Downloading {} bytes", total_size);
        
        let model_file_path = self.model_path.join(filename);
        let mut file = tokio::fs::File::create(&model_file_path).await
            .map_err(|e| MohawkError::InternalError(format!("Failed to create file: {}", e)))?;
        
        let mut downloaded = 0u64;
        let mut stream = response.bytes_stream();
        
        while let Some(chunk) = stream.next().await {
            let chunk = chunk.map_err(|e| MohawkError::InternalError(format!("Stream error: {}", e)))?;
            file.write_all(&chunk).await
                .map_err(|e| MohawkError::InternalError(format!("Write error: {}", e)))?;
            
            downloaded += chunk.len() as u64;
            if downloaded % (10 * 1024 * 1024) == 0 {
                info!("Downloaded {} MB / {} MB", 
                    downloaded / 1024 / 1024, 
                    total_size / 1024 / 1024
                );
            }
        }
        
        info!("Download complete: {:?}", model_file_path);
        Ok(model_file_path)
    }
    
    /// Load a GGUF model into memory using llama.cpp
    pub async fn load_model(&self, model_id: &str) -> Result<()> {
        let mut models = self.models.write().await;
        
        let model_data = models.get_mut(model_id)
            .ok_or_else(|| MohawkError::ModelNotFound(model_id.to_string()))?;
        
        info!("Loading model: {}", model_id);
        model_data.status = ModelStatus::Loading;
        
        // Get model file path
        let model_path = self.model_path.join(&model_data.info.path);
        
        if !model_path.exists() {
            // Try to download if it's a HuggingFace model
            if model_data.info.source == "huggingface" {
                info!("Model file not found, downloading from HuggingFace...");
                let parts: Vec<&str> = model_data.info.path.split('/').collect();
                if parts.len() >= 2 {
                    let repo_id = format!("{}/{}", parts[0], parts[1]);
                    let filename = parts[2..].join("/");
                    self.download_model(&repo_id, &filename).await?;
                } else {
                    return Err(MohawkError::ModelNotFound(
                        format!("Invalid model path format: {}", model_data.info.path)
                    ));
                }
            } else {
                return Err(MohawkError::ModelNotFound(
                    format!("Model file not found: {:?}", model_path)
                ));
            }
        }
        
        // Load model using llama.cpp
        let params = llama_cpp_2::LlamaParams::default();
        let model = llama_cpp_2::Llama::load_from_file(&model_path, params)
            .map_err(|e| MohawkError::InternalError(format!("Failed to load model: {}", e)))?;
        
        model_data.backend = Some(model);
        model_data.status = ModelStatus::Loaded;
        
        info!("Model loaded successfully: {}", model_id);
        Ok(())
    }
    
    /// Unload a model from memory
    pub async fn unload_model(&self, model_id: &str) -> Result<()> {
        let mut models = self.models.write().await;
        
        let model_data = models.get_mut(model_id)
            .ok_or_else(|| MohawkError::ModelNotFound(model_id.to_string()))?;
        
        info!("Unloading model: {}", model_id);
        model_data.status = ModelStatus::Unloaded;
        model_data.backend = None;
        
        Ok(())
    }
    
    /// Get model status
    pub async fn get_model_status(&self, model_id: &str) -> Result<ModelStatus> {
        let models = self.models.read().await;
        
        let model_data = models.get(model_id)
            .ok_or_else(|| MohawkError::ModelNotFound(model_id.to_string()))?;
        
        Ok(model_data.status.clone())
    }
    
    /// List all registered models
    pub async fn list_models(&self) -> Vec<ModelInfo> {
        let models = self.models.read().await;
        models.values().map(|m| m.info.clone()).collect()
    }
    
    /// Generate a complete response (non-streaming)
    pub async fn generate(&self, request: InferenceRequest) -> Result<InferenceResponse> {
        let model_id = request.model.clone()
            .or_else(|| self.default_model.clone())
            .ok_or_else(|| MohawkError::InvalidRequest("No model specified".to_string()))?;
        
        // Validate model is loaded
        let model_backend = {
            let models = self.models.read().await;
            let model_data = models.get(&model_id)
                .ok_or_else(|| MohawkError::ModelNotFound(model_id.clone()))?;
            
            if model_data.status != ModelStatus::Loaded {
                return Err(MohawkError::ModelNotLoaded(model_id.clone()));
            }
            
            model_data.backend.as_ref()
                .ok_or_else(|| MohawkError::ModelNotLoaded(model_id.clone()))?
                .clone()
        };
        
        // Update stats
        {
            let mut stats = self.stats.lock().await;
            stats.requests_total += 1;
        }
        
        // Build prompt from messages
        let prompt = self.build_prompt(&request.messages, request.system_prompt.as_deref());
        
        // Perform actual inference using llama.cpp
        let response_text = self.run_inference(&model_backend, &prompt, &request).await?;
        
        let response = InferenceResponse::new(
            model_id,
            Message {
                role: "assistant".to_string(),
                content: response_text,
            },
            Some("stop".to_string()),
        );
        
        info!("Generated response: {} chars", response_text.len());
        Ok(response)
    }
    
    /// Generate streaming response
    pub async fn generate_stream(
        &self,
        request: InferenceRequest,
    ) -> Result<impl futures::Stream<Item = Result<StreamToken>>> {
        let model_id = request.model.clone()
            .or_else(|| self.default_model.clone())
            .ok_or_else(|| MohawkError::InvalidRequest("No model specified".to_string()))?;
        
        // Validate model is loaded
        let model_backend = {
            let models = self.models.read().await;
            let model_data = models.get(&model_id)
                .ok_or_else(|| MohawkError::ModelNotFound(model_id.clone()))?;
            
            if model_data.status != ModelStatus::Loaded {
                return Err(MohawkError::ModelNotLoaded(model_id.clone()));
            }
            
            model_data.backend.as_ref()
                .ok_or_else(|| MohawkError::ModelNotLoaded(model_id.clone()))?
                .clone()
        };
        
        // Update stats
        {
            let mut stats = self.stats.lock().await;
            stats.requests_total += 1;
        }
        
        // Build prompt
        let prompt = self.build_prompt(&request.messages, request.system_prompt.as_deref());
        
        // Create stream with real inference
        let stream = self.create_token_stream(prompt, model_id, request, model_backend);
        
        Ok(stream)
    }
    
    /// Build prompt from conversation history
    fn build_prompt(&self, messages: &[Message], system_prompt: Option<&str>) -> String {
        let mut prompt = String::new();
        
        // Add system prompt if provided
        if let Some(system) = system_prompt {
            prompt.push_str(&format!("<|system|>\n{}\n</s>\n", system));
        }
        
        // Add conversation history in chat format
        for msg in messages {
            let role_tag = match msg.role.as_str() {
                "user" => "<|user|>",
                "assistant" => "<|assistant|>",
                "system" => "<|system|>",
                _ => "<|user|>",
            };
            prompt.push_str(&format!("{}\n{}\n</s>\n", role_tag, msg.content));
        }
        
        // Add assistant prefix
        prompt.push_str("<|assistant|>\n");
        
        prompt
    }
    
    /// Run actual inference using llama.cpp
    async fn run_inference(
        &self,
        model: &llama_cpp_2::Llama,
        prompt: &str,
        request: &InferenceRequest,
    ) -> Result<String> {
        use llama_cpp_2::LlamaContext;
        
        // Create context for inference
        let mut ctx = model.new_context()
            .map_err(|e| MohawkError::InternalError(format!("Failed to create context: {}", e)))?;
        
        // Tokenize prompt
        let tokens = ctx.tokenize(prompt.as_bytes())
            .map_err(|e| MohawkError::InternalError(format!("Tokenization failed: {}", e)))?;
        
        // Set generation parameters
        let max_tokens = request.max_tokens.unwrap_or(512) as usize;
        let temperature = request.temperature.unwrap_or(0.7) as f32;
        let top_p = request.top_p.unwrap_or(0.9) as f32;
        let top_k = request.top_k.unwrap_or(40) as i32;
        
        // Generate tokens
        let mut output = String::new();
        let mut token_count = 0;
        
        for _ in 0..max_tokens {
            // Sample next token
            let token = ctx.sample(temperature, top_k, top_p)
                .map_err(|e| MohawkError::InternalError(format!("Sampling failed: {}", e)))?;
            
            // Check for stop sequences
            if token == model.token_eos() {
                break;
            }
            
            // Convert token to string
            let token_str = model.token_to_str(token)
                .unwrap_or("");
            
            output.push_str(token_str);
            token_count += 1;
            
            // Check stop sequences
            if let Some(stops) = &request.stop {
                for stop in stops {
                    if output.ends_with(stop) {
                        return Ok(output[..output.len()-stop.len()].to_string());
                    }
                }
            }
        }
        
        // Update token stats
        {
            let mut stats = self.stats.lock().await;
            stats.tokens_generated += token_count as i64;
        }
        
        Ok(output.trim().to_string())
    }
    
    /// Create token stream for streaming responses using real inference
    fn create_token_stream(
        &self,
        prompt: String,
        model_id: String,
        request: InferenceRequest,
        model: llama_cpp_2::Llama,
    ) -> impl futures::Stream<Item = Result<StreamToken>> {
        use futures::stream::{self, StreamExt};
        use tokio::sync::mpsc;
        
        let (tx, rx) = mpsc::channel(32);
        
        tokio::spawn(async move {
            let id = format!("chatcmpl-{}", uuid::Uuid::new_v4().simple());
            let created = chrono::Utc::now().timestamp();
            
            // Send role delta first
            let _ = tx.send(Ok(StreamToken {
                id: id.clone(),
                object: "chat.completion.chunk".to_string(),
                created,
                model: model_id.clone(),
                choices: vec![StreamChoice {
                    index: 0,
                    delta: Delta {
                        role: Some("assistant".to_string()),
                        content: None,
                    },
                    finish_reason: None,
                }],
            })).await;
            
            // Create context for streaming inference
            match model.new_context() {
                Ok(mut ctx) => {
                    // Tokenize prompt
                    match ctx.tokenize(prompt.as_bytes()) {
                        Ok(_tokens) => {
                            let max_tokens = request.max_tokens.unwrap_or(512) as usize;
                            let temperature = request.temperature.unwrap_or(0.7) as f32;
                            let top_p = request.top_p.unwrap_or(0.9) as f32;
                            let top_k = request.top_k.unwrap_or(40) as i32;
                            
                            for i in 0..max_tokens {
                                // Sample next token
                                match ctx.sample(temperature, top_k, top_p) {
                                    Ok(token) => {
                                        if token == model.token_eos() {
                                            break;
                                        }
                                        
                                        if let Some(token_str) = model.token_to_str(token) {
                                            let _ = tx.send(Ok(StreamToken {
                                                id: id.clone(),
                                                object: "chat.completion.chunk".to_string(),
                                                created,
                                                model: model_id.clone(),
                                                choices: vec![StreamChoice {
                                                    index: 0,
                                                    delta: Delta {
                                                        role: None,
                                                        content: Some(token_str.to_string()),
                                                    },
                                                    finish_reason: None,
                                                }],
                                            })).await;
                                        }
                                        
                                        // Small delay for realistic streaming
                                        tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
                                    }
                                    Err(e) => {
                                        error!("Sampling error: {}", e);
                                        break;
                                    }
                                }
                            }
                        }
                        Err(e) => {
                            error!("Tokenization error: {}", e);
                            let _ = tx.send(Err(MohawkError::InternalError(
                                format!("Tokenization failed: {}", e)
                            ))).await;
                        }
                    }
                }
                Err(e) => {
                    error!("Context creation error: {}", e);
                    let _ = tx.send(Err(MohawkError::InternalError(
                        format!("Context creation failed: {}", e)
                    ))).await;
                }
            }
            
            // Send finish reason
            let _ = tx.send(Ok(StreamToken {
                id: id.clone(),
                object: "chat.completion.chunk".to_string(),
                created,
                model: model_id,
                choices: vec![StreamChoice {
                    index: 0,
                    delta: Delta {
                        role: None,
                        content: None,
                    },
                    finish_reason: Some("stop".to_string()),
                }],
            })).await;
        });
        
        stream::unfold(rx, |mut rx| async move {
            rx.recv().await.map(|res| (res, rx))
        })
    }
    
    /// Get engine statistics
    pub async fn get_stats(&self) -> HealthResponse {
        let stats = self.stats.lock().await;
        let models = self.models.read().await;
        let models_loaded = models.values()
            .filter(|m| m.status == ModelStatus::Loaded)
            .count() as i32;
        
        HealthResponse {
            status: "healthy".to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            uptime_secs: stats.start_time.elapsed().as_secs(),
            models_loaded,
            requests_total: stats.requests_total,
        }
    }
    
    /// Set default model
    pub fn set_default_model(&mut self, model_id: &str) {
        self.default_model = Some(model_id.to_string());
        info!("Default model set to: {}", model_id);
    }
}

impl Default for InferenceEngine {
    fn default() -> Self {
        Self::new(None).unwrap()
    }
}
