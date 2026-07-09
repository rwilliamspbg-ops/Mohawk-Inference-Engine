//! Mohawk Inference Engine - Production-ready LLM serving
//!
//! A high-performance inference engine with OpenAI-compatible API,
//! streaming support, and enterprise features.

mod api;
mod engine;
mod error;
mod models;
mod server;

pub use engine::InferenceEngine;
pub use error::{MohawkError, Result};
pub use models::{
    ChatChoice, InferenceRequest, InferenceResponse, Message, ModelInfo, ModelStatus,
    StreamResponse, StreamToken, Usage,
};
pub use server::{start_default, Server, ServerConfig};

use tracing::info;

/// Initialize logging with JSON format for production
pub fn init_logging() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("mohawk_server=info".parse().unwrap())
                .add_directive("axum=info".parse().unwrap()),
        )
        .json()
        .init();

    info!("Mohawk Inference Engine initialized");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_creation() {
        let engine = InferenceEngine::new(None);
        assert!(engine.is_ok());
    }

    #[tokio::test]
    async fn test_inference_request() {
        let engine = InferenceEngine::new(None).unwrap();
        engine
            .register_model(ModelInfo {
                id: "test-model".to_string(),
                name: "Test Model".to_string(),
                parameters: "1B".to_string(),
                quantization: "Q4".to_string(),
                size_gb: 1.0,
                loaded: false,
            })
            .await
            .unwrap();
        engine.load_model("test-model").await.unwrap();
        let request = InferenceRequest {
            messages: vec![Message {
                role: "user".to_string(),
                content: "Hello!".to_string(),
            }],
            model: Some("test-model".to_string()),
            temperature: Some(0.7),
            top_p: None,
            top_k: None,
            max_tokens: Some(100),
            stream: false,
            stop: None,
            system_prompt: None,
        };

        let response = engine.generate(request).await;
        assert!(response.is_ok());
    }
}
