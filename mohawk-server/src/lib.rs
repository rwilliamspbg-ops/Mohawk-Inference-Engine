//! Mohawk Inference Engine - Production-ready LLM serving
//! 
//! A high-performance inference engine with OpenAI-compatible API,
//! streaming support, and enterprise features.

mod error;
mod models;
mod engine;
mod api;
mod server;

pub use error::{MohawkError, Result};
pub use models::{
    Message, InferenceRequest, InferenceResponse, ChatChoice, Usage,
    StreamToken, StreamResponse, ModelInfo, ModelStatus
};
pub use engine::InferenceEngine;
pub use server::Server;

use tracing::info;

/// Initialize logging with JSON format for production
pub fn init_logging() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("mohawk_server=info".parse().unwrap())
                .add_directive("axum=info".parse().unwrap())
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
        let engine = InferenceEngine::new();
        assert!(engine.is_ok());
    }
    
    #[tokio::test]
    async fn test_inference_request() {
        let engine = InferenceEngine::new().unwrap();
        let request = InferenceRequest {
            messages: vec![Message {
                role: "user".to_string(),
                content: "Hello!".to_string(),
            }],
            model: None,
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
