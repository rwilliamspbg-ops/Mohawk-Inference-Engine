//! Error types for Mohawk Inference Engine

use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;
use thiserror::Error;

/// Main error type for Mohawk
#[derive(Error, Debug)]
pub enum MohawkError {
    #[error("Model not found: {0}")]
    ModelNotFound(String),

    #[error("Model not loaded: {0}")]
    ModelNotLoaded(String),

    #[error("Invalid request: {0}")]
    InvalidRequest(String),

    #[error("Inference failed: {0}")]
    InferenceFailed(String),

    #[error("Tokenization error: {0}")]
    TokenizationError(String),

    #[error("Backend error: {0}")]
    BackendError(String),

    #[error("Internal server error: {0}")]
    InternalError(String),

    #[error("Rate limit exceeded")]
    RateLimitExceeded,

    #[error("Authentication failed")]
    AuthenticationFailed,
}

impl IntoResponse for MohawkError {
    fn into_response(self) -> Response {
        let (status, error_message) = match &self {
            MohawkError::ModelNotFound(msg) => (
                StatusCode::NOT_FOUND,
                json!({"error": {"message": msg, "type": "model_not_found"}}),
            ),
            MohawkError::ModelNotLoaded(msg) => (
                StatusCode::BAD_REQUEST,
                json!({"error": {"message": msg, "type": "model_not_loaded"}}),
            ),
            MohawkError::InvalidRequest(msg) => (
                StatusCode::BAD_REQUEST,
                json!({"error": {"message": msg, "type": "invalid_request_error"}}),
            ),
            MohawkError::InferenceFailed(msg) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                json!({"error": {"message": msg, "type": "inference_error"}}),
            ),
            MohawkError::TokenizationError(msg) => (
                StatusCode::BAD_REQUEST,
                json!({"error": {"message": msg, "type": "tokenization_error"}}),
            ),
            MohawkError::BackendError(msg) => (
                StatusCode::SERVICE_UNAVAILABLE,
                json!({"error": {"message": msg, "type": "backend_error"}}),
            ),
            MohawkError::RateLimitExceeded => (
                StatusCode::TOO_MANY_REQUESTS,
                json!({"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}),
            ),
            MohawkError::AuthenticationFailed => (
                StatusCode::UNAUTHORIZED,
                json!({"error": {"message": "Authentication failed", "type": "authentication_error"}}),
            ),
            MohawkError::InternalError(msg) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                json!({"error": {"message": msg, "type": "internal_error"}}),
            ),
        };

        (status, Json(error_message)).into_response()
    }
}

/// Result type alias
pub type Result<T> = std::result::Result<T, MohawkError>;

impl From<std::io::Error> for MohawkError {
    fn from(err: std::io::Error) -> Self {
        MohawkError::BackendError(err.to_string())
    }
}
