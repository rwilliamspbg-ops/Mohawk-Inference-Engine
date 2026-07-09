//! Mohawk Inference Server - Main Entry Point

use mohawk_server::{Server, ServerConfig};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Parse command line arguments or use defaults
    let host = std::env::var("MOHAWK_HOST").unwrap_or_else(|_| "0.0.0.0".to_string());
    let port: u16 = std::env::var("MOHAWK_PORT")
        .unwrap_or_else(|_| "8080".to_string())
        .parse()
        .unwrap_or(8080);
    
    let config = ServerConfig {
        host,
        port,
        default_model: None,
    };
    
    let server = Server::new(config)?;
    server.run().await
}
