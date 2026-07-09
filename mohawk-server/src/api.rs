//! API routes for Mohawk Inference Engine
//! OpenAI-compatible REST API

use axum::{
    extract::State,
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use futures::StreamExt;
use serde_json::json;
use tower_http::cors::{Any, CorsLayer};
use tracing::{info, error};

use crate::engine::InferenceEngine;
use crate::error::MohawkError;
use crate::models::*;

/// Application state shared across routes
#[derive(Clone)]
pub struct AppState {
    pub engine: InferenceEngine,
}

/// Create the API router with all endpoints
pub fn create_router(engine: InferenceEngine) -> Router {
    let state = AppState { engine };
    
    // Configure CORS for GUI access
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);
    
    Router::new()
        // Health & metrics
        .route("/health", get(health_check))
        .route("/metrics", get(get_metrics))
        
        // Model management (OpenAI compatible)
        .route("/v1/models", get(list_models))
        .route("/v1/models/:model_id", get(get_model))
        
        // Model loading/unloading (Mohawk extension)
        .route("/api/models/load", post(load_model))
        .route("/api/models/unload", post(unload_model))
        
        // Chat completions (OpenAI compatible)
        .route("/v1/chat/completions", post(chat_completions))
        
        // Legacy completions
        .route("/v1/completions", post(completions))
        
        .layer(cors)
        .with_state(state)
}

/// Health check endpoint
async fn health_check(State(state): State<AppState>) -> Json<HealthResponse> {
    let stats = state.engine.get_stats().await;
    Json(stats)
}

/// Metrics endpoint (Prometheus format)
async fn get_metrics(State(state): State<AppState>) -> impl IntoResponse {
    let stats = state.engine.get_stats().await;
    
    let metrics = format!(
        r#"# HELP mohawk_uptime_seconds Server uptime in seconds
# TYPE mohawk_uptime_seconds counter
mohawk_uptime_seconds {}

# HELP mohawk_requests_total Total number of requests
# TYPE mohawk_requests_total counter
mohawk_requests_total {}

# HELP mohawk_models_loaded Number of loaded models
# TYPE mohawk_models_loaded gauge
mohawk_models_loaded {}
"#,
        stats.uptime_secs,
        stats.requests_total,
        stats.models_loaded
    );
    
    (StatusCode::OK, metrics)
}

/// List available models (OpenAI compatible)
async fn list_models(State(state): State<AppState>) -> Json<ModelListResponse> {
    let models = state.engine.list_models().await;
    
    Json(ModelListResponse {
        object: "list".to_string(),
        data: models,
    })
}

/// Get specific model details
async fn get_model(
    State(state): State<AppState>,
    axum::extract::Path(model_id): axum::extract::Path<String>,
) -> Result<Json<ModelInfo>, MohawkError> {
    let models = state.engine.list_models().await;
    
    let model = models.into_iter()
        .find(|m| m.id == model_id)
        .ok_or_else(|| MohawkError::ModelNotFound(model_id))?;
    
    Ok(Json(model))
}

/// Load a model into memory
async fn load_model(
    State(state): State<AppState>,
    Json(payload): Json<serde_json::Value>,
) -> Result<impl IntoResponse, MohawkError> {
    let model_id = payload["model_id"]
        .as_str()
        .ok_or_else(|| MohawkError::InvalidRequest("model_id required".to_string()))?
        .to_string();
    
    state.engine.load_model(&model_id).await?;
    
    info!("Model loaded: {}", model_id);
    Ok((StatusCode::OK, Json(json!({
        "success": true,
        "model_id": model_id,
        "status": "loaded"
    }))))
}

/// Unload a model from memory
async fn unload_model(
    State(state): State<AppState>,
    Json(payload): Json<serde_json::Value>,
) -> Result<impl IntoResponse, MohawkError> {
    let model_id = payload["model_id"]
        .as_str()
        .ok_or_else(|| MohawkError::InvalidRequest("model_id required".to_string()))?
        .to_string();
    
    state.engine.unload_model(&model_id).await?;
    
    info!("Model unloaded: {}", model_id);
    Ok((StatusCode::OK, Json(json!({
        "success": true,
        "model_id": model_id,
        "status": "unloaded"
    }))))
}

/// Chat completions endpoint (OpenAI compatible)
async fn chat_completions(
    State(state): State<AppState>,
    Json(request): Json<InferenceRequest>,
) -> Result<Response, MohawkError> {
    if request.stream {
        // Streaming response
        let stream = state.engine.generate_stream(request).await?;
        
        let stream_body = axum::body::Body::from_stream(
            stream.map(|result| {
                match result {
                    Ok(token) => {
                        let json = serde_json::to_string(&token).unwrap();
                        Ok::<_, MohawkError>(format!("data: {}\n\n", json))
                    }
                    Err(e) => {
                        error!("Stream error: {}", e);
                        Ok("data: [DONE]\n\n".to_string())
                    }
                }
            })
        );
        
        Ok((
            StatusCode::OK,
            [("Content-Type", "text/event-stream")],
            stream_body,
        ).into_response())
    } else {
        // Non-streaming response
        let response = state.engine.generate(request).await?;
        Ok(Json(response).into_response())
    }
}

/// Legacy completions endpoint
async fn completions(
    State(state): State<AppState>,
    Json(payload): Json<serde_json::Value>,
) -> Result<impl IntoResponse, MohawkError> {
    // Convert legacy format to chat format
    let prompt = payload["prompt"]
        .as_str()
        .unwrap_or("")
        .to_string();
    
    let messages = vec![Message {
        role: "user".to_string(),
        content: prompt,
    }];
    
    let request = InferenceRequest {
        messages,
        model: payload["model"].as_str().map(|s| s.to_string()),
        temperature: payload["temperature"].as_f64().map(|f| f as f32),
        top_p: payload["top_p"].as_f64().map(|f| f as f32),
        top_k: payload.get("top_k").and_then(|v| v.as_i64()).map(|i| i as i32),
        max_tokens: payload.get("max_tokens").and_then(|v| v.as_i64()).map(|i| i as i32),
        stream: payload["stream"].as_bool().unwrap_or(false),
        stop: payload.get("stop").and_then(|v| v.as_array()).map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect()
        }),
        system_prompt: None,
    };
    
    let response = state.engine.generate(request).await?;
    Ok(Json(response))
}
