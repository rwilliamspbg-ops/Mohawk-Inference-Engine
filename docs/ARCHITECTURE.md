Mohawk Inference Engine — Architecture Spec

Overview

Goal: provide a production-grade inference engine that enables capabilities LM Studio does not: multi-device layer splitting, PQC-secured edge offload, and high-concurrency session management. This document describes the core subsystems, dataflows, APIs, security model, and implementation priorities for an MVP.

1. Core concepts

- Layer-splitting: partitioning a neural network at layer boundaries (or sub-layer blocks) so different partitions (slices) execute on different devices (GPU/NPU/CPU/edge). Each slice exposes a small runtime ABI for input/output activation tensors and metadata.
- Offload: the act of sending one or more slices to a remote device for execution. Offloads must preserve confidentiality/integrity of model IP (weights) and activations as required by policy.
- PQC-secured channel: post-quantum cryptography handshake + authenticated encryption for slice packages and RPC traffic.
- Session manager: long-lived controller that maps client sessions to slice placements, manages QoS, adaptive batching, autoscaling, and failure recovery.

2. High-level architecture

Components:
- Controller (central or local): plans partitioning, placement, and routes requests to workers.
- Worker runtime: lightweight process on each device that accepts slice packages, registers capabilities (memory, device type), and executes slices.
- Offload transport: secure RPC over TCP/QUIC with PQC handshake and integrity checks.
- Session Manager: receives client requests, handles session state, batching, and QoS rules.
- Scheduler: maps slices to workers, performs placement decisions using cost model and current telemetry.
- Persistence: key/value store for slice metadata, session state, and logs (can be local filesystem or etcd for distributed setups).

3. Layer-splitting design

3.1 Partitioning model
- Static split: for MVP, support deterministic splits at transformer block or attention/MLP block granularity. Input: model graph (ONNX, TorchScript), cost model, device inventory. Output: ordered list of slices with boundary tensor shapes and serialization descriptors.
- Dynamic split (future): runtime re-partitioning based on latency/throughput signals.

3.2 Slice format
- Metadata: slice id, inputs/outputs shapes, parameter size, expected memory footprint, device hints, version, policy tags (private/public).
- Artifact: serialized weights in compact format (FP16/int8 quantized optional) + small runtime glue to map tensor ops.
- Transport container: authenticated envelope (PQC AEAD) + optional compression.

3.3 Runtime ABI
- Execute(slice_id, input_tensor, trace_id) -> output_tensor, metrics
- Health(check) -> status
- Preload(slice_id) -> ack

3.4 Scheduling and placement
- Cost model inputs: parameter size, compute FLOPs per-token, estimated activation sizes, device throughput and free memory, network latency.
- Heuristics for MVP: place compute-heavy contiguous slices on GPU if available; place small parameter slices on CPU to lower memory duplication; prefer colocated slices to reduce network hops.
- Backpressure: if a worker is loaded, controller routes slice to alternate worker or falls back to local execution.

4. PQC-secured edge offload

4.1 Security goals
- Confidentiality of slice weights when policy requires (IP protection).
- Integrity of slice artifacts and runtime RPCs.
- Forward-secure key exchange resistant to quantum-capable adversaries.

4.2 Keyflows and handshakes
- Root authority: operator provides long-term signing key (classical/ECDSA) for worker identity; optionally use hardware TPM for key storage.
- Session handshake: use a PQC KEM (e.g., Kyber or later NIST standard) to establish ephemeral symmetric AEAD keys per connection. Steps:
  1. Controller/worker exchange identity-signed certificates (classical) and PQC KEM public values.
  2. Both sides derive AEAD keys via HKDF over KEM shared secret and transcript.
  3. Optionally request remote attestation token before accepting slices (attestation hooks, e.g., Intel SGX/SEV or MDS attestation APIs).

4.3 Slice packaging & integrity
- Each slice package: {manifest, weights.blob, signature, version}
- Manifest contains policy tags; controller encrypts package with AEAD key and includes HMAC/signature for extra assurance.
- Workers verify signature + AEAD before load.

4.4 Performance considerations
- PQC KEM handshake cost is paid per long-lived connection; reuse AEAD keys for multiple RPCs.
- For high-throughput edge fleets, pre-provision slice packages to workers via provisioning channel to avoid repeated KEM costs.

5. Session manager

5.1 API (gRPC/HTTP)
- StartSession(request {model, routingHints, qos, tenant}) -> session_id
- Infer(session_id, input, options {sync|async}) -> response stream or token
- EndSession(session_id)
- GetSessionStats(session_id) -> metrics

5.2 Session lifecycle
- Session creation: controller allocates slices, populates placement plan, preloads prioritized slices on workers, returns session token.
- Execution path: client -> session manager -> controller splits request across slices -> workers execute in pipeline -> session manager aggregates outputs.
- Adaptive batching: session manager groups small inferences into micro-batches per slice based on configured latency budgets.

5.3 QoS and isolation
- Per-session resource caps (max concurrency, token rate).
- Tenant isolation: per-tenant slice caching and optional model duplication flags.
- Fair queuing or priority queues for low-latency sessions.

6. Telemetry & metrics
- Per-slice metrics: exec latency, memory usage, throughput, error rate.
- Per-worker metrics: GPU util, free memory, network RTT, connection counts.
- Per-session metrics: p50/p95/p99 latencies, batch sizes, tokens/sec.
- Emit via Prometheus metrics endpoint and structured traces (OpenTelemetry) for tracing across slices.

7. Failure modes and fallbacks
- Worker failure: controller reroutes to alternate worker or triggers local fallback (single-node execution). Evict/restore policy for preloaded slices.
- Network partition: fall back to local execution when possible; if offload required, return graceful degradation messages to client.
- Mismatched versions: use manifest version checks to prevent executing incompatible slices.

8. Interfaces & data formats
- Model ingestion: accept ONNX and TorchScript (MVP) with translator that enumerates layer boundaries.
- Slice artifact: gzipped protobuf or tar with manifest.json and weights.bin.
- RPC: gRPC over QUIC (preferred) or HTTP/2 with AEAD wrapper.

9. Testing & benchmarks
- Unit tests: correctness of slice outputs vs baseline single-node for a suite of models.
- Integration tests: end-to-end run across two devices (GPU + CPU) validating activations and outputs.
- Load tests: simulate 1k concurrent sessions with synthetic clients, measure p95 latency and throughput.
- Security tests: verify PQC handshake, replay protection, and attestation flows.

10. MVP milestones and deliverables
- Week 0–1: architecture doc, slice format, and prototype plan. (this doc)
- Week 1–2: implement controller + worker minimal runtime and static partitioner that accepts a small transformer and emits slices.
- Week 2–3: add PQC handshake, encrypted slice transport, and pre-provisioning flow.
- Week 3–4: session manager with adaptive batching and basic QoS; run 1k simulated sessions.
- Week 4–5: integration tests, telemetry dashboard, readme hero docs, and release prep.

11. Open questions
- Target PQC primitives (Kyber, CRYSTALS-Kyber; choose current NIST-recommended variant). Decide whether to include hybrid classical+PQC key exchange.
- Attestation strategy for diverse edge hardware — what minimal attestation APIs should we support for MVP?
- Benchmark targets: supply representative hardware profiles to set realistic throughput/latency goals.

Appendix: quick dataflow
1. `StartSession` -> controller computes split plan -> preloads slices to assigned workers (encrypted transfer).
2. Client sends `Infer` -> session manager pipelines activations across workers over secure channels.
3. Workers return outputs and metrics -> session manager aggregates and returns response.

Next steps: implement the static partitioner and minimal worker runtime (Week 1 task).