# Mohawk Inference Engine - CPU Version
FROM rust:1.87-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    git \
    clang \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

ENV CC=clang
ENV CXX=clang++

# Copy source code
COPY Cargo.toml Cargo.lock* ./
COPY src/ ./src/

# Build release binary
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/target/release/mohawk-server /app/mohawk-server

# Create models directory
RUN mkdir -p /app/models

EXPOSE 8080

ENV RUST_LOG=info
ENV MODEL_PATH=/app/models

ENTRYPOINT ["/app/mohawk-server"]
