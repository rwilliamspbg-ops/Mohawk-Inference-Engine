//! Core inference engine implementation

use crate::error::{MohawkError, Result};
use crate::models::*;
use futures::{stream, StreamExt};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::{Mutex, RwLock};
use tracing::info;

/// Main inference engine managing models and generation
#[derive(Clone)]
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
}

struct EngineStats {
    requests_total: i64,
    tokens_generated: i64,
    start_time: std::time::Instant,
}

impl Default for EngineStats {
    fn default() -> Self {
        Self {
            requests_total: 0,
            tokens_generated: 0,
            start_time: std::time::Instant::now(),
        }
    }
}

impl InferenceEngine {
    /// Create a new inference engine with custom model path
    pub fn new(model_path: Option<PathBuf>) -> Result<Self> {
        let path = model_path.unwrap_or_else(|| PathBuf::from("./models"));

        info!("Initializing Mohawk Inference Engine");
        info!("Model storage path: {:?}", path);

        if !path.exists() {
            std::fs::create_dir_all(&path).map_err(|e| {
                MohawkError::InternalError(format!("Failed to create model directory: {e}"))
            })?;
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
            return Err(MohawkError::InvalidRequest(format!(
                "Model {} already registered",
                model_info.id
            )));
        }

        models.insert(
            model_info.id.clone(),
            ModelData {
                info: model_info.clone(),
                status: ModelStatus::Unloaded,
            },
        );
        info!("Registered model: {}", model_info.id);

        Ok(())
    }

    /// Download a model from HuggingFace
    pub async fn download_model(&self, repo_id: &str, filename: &str) -> Result<PathBuf> {
        use reqwest::Client;
        use tokio::io::AsyncWriteExt;

        let url = format!("https://huggingface.co/{repo_id}/resolve/main/{filename}");
        info!("Downloading model from: {}", url);

        let client = Client::new();
        let response = client
            .get(&url)
            .send()
            .await
            .map_err(|e| MohawkError::InternalError(format!("Download failed: {e}")))?;

        if !response.status().is_success() {
            return Err(MohawkError::InternalError(format!(
                "Download failed with status: {}",
                response.status()
            )));
        }

        let total_size = response
            .content_length()
            .ok_or_else(|| MohawkError::InternalError("Unknown content length".to_string()))?;

        info!("Downloading {} bytes", total_size);

        let model_file_path = self.model_path.join(filename);
        let mut file = tokio::fs::File::create(&model_file_path)
            .await
            .map_err(|e| MohawkError::InternalError(format!("Failed to create file: {e}")))?;

        let mut downloaded = 0u64;
        let mut response_stream = response.bytes_stream();

        while let Some(chunk) = response_stream.next().await {
            let chunk =
                chunk.map_err(|e| MohawkError::InternalError(format!("Stream error: {e}")))?;
            file.write_all(&chunk)
                .await
                .map_err(|e| MohawkError::InternalError(format!("Write error: {e}")))?;

            downloaded += chunk.len() as u64;
            if downloaded.is_multiple_of(10 * 1024 * 1024) {
                info!(
                    "Downloaded {} MB / {} MB",
                    downloaded / 1024 / 1024,
                    total_size / 1024 / 1024
                );
            }
        }

        info!("Download complete: {:?}", model_file_path);
        Ok(model_file_path)
    }

    /// Mark a registered model as loaded.
    pub async fn load_model(&self, model_id: &str) -> Result<()> {
        let mut models = self.models.write().await;
        let model_data = models
            .get_mut(model_id)
            .ok_or_else(|| MohawkError::ModelNotFound(model_id.to_string()))?;

        info!("Loading model: {}", model_id);
        model_data.status = ModelStatus::Loading;
        model_data.info.loaded = true;
        model_data.status = ModelStatus::Loaded;

        info!("Model loaded successfully: {}", model_id);
        Ok(())
    }

    /// Unload a model from memory
    pub async fn unload_model(&self, model_id: &str) -> Result<()> {
        let mut models = self.models.write().await;
        let model_data = models
            .get_mut(model_id)
            .ok_or_else(|| MohawkError::ModelNotFound(model_id.to_string()))?;

        info!("Unloading model: {}", model_id);
        model_data.status = ModelStatus::Unloaded;
        model_data.info.loaded = false;

        Ok(())
    }

    /// Get model status
    pub async fn get_model_status(&self, model_id: &str) -> Result<ModelStatus> {
        let models = self.models.read().await;
        let model_data = models
            .get(model_id)
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
        let model_id = request
            .model
            .clone()
            .or_else(|| self.default_model.clone())
            .ok_or_else(|| MohawkError::InvalidRequest("No model specified".to_string()))?;

        self.ensure_model_loaded(&model_id).await?;

        {
            let mut stats = self.stats.lock().await;
            stats.requests_total += 1;
        }

        let prompt = self.build_prompt(&request.messages, request.system_prompt.as_deref());
        let response_text = self.simulate_inference(&prompt, &request).await?;

        let response = InferenceResponse::new(
            model_id,
            Message {
                role: "assistant".to_string(),
                content: response_text,
            },
            Some("stop".to_string()),
        );

        info!(
            "Generated response: {} chars",
            response.choices[0].message.content.len()
        );
        Ok(response)
    }

    /// Generate streaming response
    pub async fn generate_stream(
        &self,
        request: InferenceRequest,
    ) -> Result<impl futures::Stream<Item = Result<StreamToken>>> {
        let model_id = request
            .model
            .clone()
            .or_else(|| self.default_model.clone())
            .ok_or_else(|| MohawkError::InvalidRequest("No model specified".to_string()))?;

        self.ensure_model_loaded(&model_id).await?;

        {
            let mut stats = self.stats.lock().await;
            stats.requests_total += 1;
        }

        let prompt = self.build_prompt(&request.messages, request.system_prompt.as_deref());
        Ok(self.create_token_stream(prompt, model_id, request))
    }

    /// Build prompt from conversation history
    fn build_prompt(&self, messages: &[Message], system_prompt: Option<&str>) -> String {
        let mut prompt = String::new();

        if let Some(system) = system_prompt {
            prompt.push_str(&format!("<|system|>\n{}\n</s>\n", system));
        }

        for msg in messages {
            let role_tag = match msg.role.as_str() {
                "user" => "<|user|>",
                "assistant" => "<|assistant|>",
                "system" => "<|system|>",
                _ => "<|user|>",
            };
            prompt.push_str(&format!("{}\n{}\n</s>\n", role_tag, msg.content));
        }

        prompt.push_str("<|assistant|>\n");
        prompt
    }

    async fn ensure_model_loaded(&self, model_id: &str) -> Result<()> {
        let models = self.models.read().await;
        let model_data = models
            .get(model_id)
            .ok_or_else(|| MohawkError::ModelNotFound(model_id.to_string()))?;

        if model_data.status != ModelStatus::Loaded {
            return Err(MohawkError::ModelNotLoaded(model_id.to_string()));
        }

        Ok(())
    }

    async fn simulate_inference(&self, prompt: &str, request: &InferenceRequest) -> Result<String> {
        let response = request
            .messages
            .iter()
            .rev()
            .find(|message| message.role == "user")
            .map(|message| format!("Mohawk placeholder response: {}", message.content))
            .unwrap_or_else(|| format!("Mohawk placeholder response for prompt: {}", prompt));

        let trimmed = if let Some(max_tokens) = request.max_tokens {
            let max_words = max_tokens.max(1) as usize;
            response
                .split_whitespace()
                .take(max_words)
                .collect::<Vec<_>>()
                .join(" ")
        } else {
            response
        };

        let completion_tokens = trimmed.split_whitespace().count() as i64;
        let mut stats = self.stats.lock().await;
        stats.tokens_generated += completion_tokens;

        Ok(trimmed)
    }

    /// Create token stream for streaming responses.
    fn create_token_stream(
        &self,
        prompt: String,
        model_id: String,
        request: InferenceRequest,
    ) -> impl futures::Stream<Item = Result<StreamToken>> {
        use tokio::sync::mpsc;

        let (tx, rx) = mpsc::channel(32);

        tokio::spawn(async move {
            let id = format!("chatcmpl-{}", uuid::Uuid::new_v4().simple());
            let created = chrono::Utc::now().timestamp();

            let _ = tx
                .send(Ok(StreamToken {
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
                }))
                .await;

            let response = request
                .messages
                .iter()
                .rev()
                .find(|message| message.role == "user")
                .map(|message| format!("Mohawk placeholder response: {}", message.content))
                .unwrap_or_else(|| format!("Mohawk placeholder response for prompt: {}", prompt));

            let max_words = request.max_tokens.unwrap_or(512).max(1) as usize;
            for token in response.split_whitespace().take(max_words) {
                let _ = tx
                    .send(Ok(StreamToken {
                        id: id.clone(),
                        object: "chat.completion.chunk".to_string(),
                        created,
                        model: model_id.clone(),
                        choices: vec![StreamChoice {
                            index: 0,
                            delta: Delta {
                                role: None,
                                content: Some(format!("{token} ")),
                            },
                            finish_reason: None,
                        }],
                    }))
                    .await;
                tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
            }

            let _ = tx
                .send(Ok(StreamToken {
                    id,
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
                }))
                .await;
        });

        stream::unfold(
            rx,
            |mut rx| async move { rx.recv().await.map(|res| (res, rx)) },
        )
    }

    /// Get engine statistics
    pub async fn get_stats(&self) -> HealthResponse {
        let stats = self.stats.lock().await;
        let models = self.models.read().await;
        let models_loaded = models
            .values()
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
        Self::new(None).expect("failed to initialize default inference engine")
    }
}
