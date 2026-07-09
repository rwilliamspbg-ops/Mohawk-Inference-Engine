//! Mohawk Inference Server
//! Production-ready HTTP server with OpenAI-compatible API

use crate::api;
use crate::engine::InferenceEngine;
use crate::init_logging;
use axum::Router;
use std::net::SocketAddr;
use tokio::net::TcpListener;
use tracing::info;

/// Server configuration
#[derive(Debug, Clone)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub default_model: Option<String>,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            host: "0.0.0.0".to_string(),
            port: 8080,
            default_model: None,
        }
    }
}

/// Main server instance
pub struct Server {
    config: ServerConfig,
    engine: InferenceEngine,
}

impl Server {
    /// Create a new server with configuration
    pub fn new(config: ServerConfig) -> Result<Self, crate::error::MohawkError> {
        let mut engine = InferenceEngine::new(None)?;
        if let Some(default_model) = config.default_model.as_deref() {
            engine.set_default_model(default_model);
        }

        Ok(Self { config, engine })
    }

    /// Register default models for the server
    pub async fn register_default_models(&self) -> Result<(), crate::error::MohawkError> {
        // Register pre-configured models (similar to LM Studio)
        let models = vec![
            crate::models::ModelInfo {
                id: "llama-3.2-3b-instruct-q4_k_m".to_string(),
                name: "Llama 3.2 3B Instruct (Q4_K_M)".to_string(),
                parameters: "3B".to_string(),
                quantization: "Q4_K_M".to_string(),
                size_gb: 2.1,
                loaded: false,
            },
            crate::models::ModelInfo {
                id: "mistral-7b-instruct-v0.3-q4_k_m".to_string(),
                name: "Mistral 7B Instruct v0.3 (Q4_K_M)".to_string(),
                parameters: "7B".to_string(),
                quantization: "Q4_K_M".to_string(),
                size_gb: 4.4,
                loaded: false,
            },
            crate::models::ModelInfo {
                id: "phi-3-mini-4k-instruct-q4_k_m".to_string(),
                name: "Phi-3 Mini 4K Instruct (Q4_K_M)".to_string(),
                parameters: "3.8B".to_string(),
                quantization: "Q4_K_M".to_string(),
                size_gb: 2.3,
                loaded: false,
            },
        ];

        for model in models {
            self.engine.register_model(model).await?;
        }

        info!("Registered {} default models", 3);
        Ok(())
    }

    /// Build the Axum router
    fn build_router(&self) -> Router {
        api::create_router(self.engine.clone())
    }

    /// Start the server
    pub async fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        init_logging();

        // Register default models
        self.register_default_models().await?;

        let addr: SocketAddr = format!("{}:{}", self.config.host, self.config.port).parse()?;

        let router = self.build_router();

        info!("🦅 Mohawk Inference Engine starting on http://{}", addr);
        info!("API endpoints:");
        info!("  - Health:     GET  http://{}/health", addr);
        info!("  - Models:     GET  http://{}/v1/models", addr);
        info!("  - Load:       POST http://{}/api/models/load", addr);
        info!("  - Unload:     POST http://{}/api/models/unload", addr);
        info!("  - Chat:       POST http://{}/v1/chat/completions", addr);
        info!("  - Metrics:    GET  http://{}/metrics", addr);
        info!("");
        info!(
            "OpenAI Compatible: Use with any OpenAI SDK by setting base_url to http://{}",
            addr
        );

        let listener = TcpListener::bind(addr).await?;
        axum::serve(listener, router).await?;

        Ok(())
    }

    /// Get the engine instance for testing
    pub fn engine(&self) -> &InferenceEngine {
        &self.engine
    }
}

/// Start server with default configuration
pub async fn start_default() -> Result<(), Box<dyn std::error::Error>> {
    let config = ServerConfig::default();
    let server = Server::new(config)?;
    server.run().await
}
