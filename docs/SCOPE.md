Scope & Success Criteria

Target: platform and infrastructure engineers, MLOps teams, and edge fleet operators who need production-grade inference beyond single-node setups.

MVP capabilities:
- Multi-device layer splitting: demonstrate partitioning a medium-sized transformer across GPU and CPU with deterministic correctness and end-to-end inference.
- Secure edge offload: implement PQC-based encryption and integrity checks for offloaded model slices and communications.
- High-concurrency session management: support 1k+ concurrent lightweight sessions with per-session QoS and adaptive batching.

Success metrics:
- Correctness: identical outputs (within numerical tolerance) compared to single-node baseline for partitioned runs.
- Performance: 2× throughput improvement for target hardware when split across devices (measured on prototype hardware), and median p95 latency within target SLA for 95% of sessions.
- Security: PQC handshake and slice integrity checks complete within acceptable overhead (<20% added latency in offload path) and keys/telemetry never expose raw weights.

Out of scope for MVP:
- Full production orchestration (K8s operators) and UI consoles — focus is on core engine, APIs, and integrations.

Next: architecture spec covering layer-splitting algorithm, PQC keyflows, and session manager APIs.