liboqs (pyOQS) integration notes

Goal: Replace the placeholder X25519-only `PQCAdapter` with a hybrid KEM based on liboqs (e.g., Kyber) + X25519.

High level steps:

1. Install native liboqs and Python bindings (pyOQS).
   - On Ubuntu (example):
     ```bash
     sudo apt-get update
     sudo apt-get install -y build-essential cmake libssl-dev pkg-config
     # Build and install liboqs from source (follow liboqs README)
     git clone --branch main https://github.com/open-quantum-safe/liboqs.git
     cd liboqs
     mkdir build && cd build
     cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
     make -j$(nproc)
     sudo make install
     
     # Install pyOQS (Python bindings)
     pip install pyOQS
     ```
   - Alternatively use your distribution's packages or a prepared devcontainer that installs liboqs.

2. Update `prototype/crypto.py` to perform a proper KEM exchange during handshake:
   - Controller: send X25519 pub + OQS pub to worker.
   - Worker: encapsulate to controller's OQS pub -> return encapsulation ciphertext + worker OQS pub.
   - Controller: decapsulate ciphertext to obtain OQS shared secret.
   - Final symmetric AEAD key = HKDF(X25519_shared || OQS_shared)

3. Tests & validation:
   - Run `prototype/test_secure_run.py` and `prototype/load_harness.py` to validate encrypted flows.
   - Ensure the worker `/handshake` returns `worker_oqs_pub_b64` and `worker_pub_b64`.

Notes:
- The repository already contains scaffolding in `prototype/crypto.py` to detect pyOQS at runtime and expose `get_oqs_public()`; complete integration requires invoking `kem.encapsulate()` and `kem.decapsulate()` where appropriate.
- Building liboqs on CI requires adding native build steps in the pipeline; consider a GitHub Actions matrix job with a prebuilt liboqs artifact or using a self-hosted runner.

If you want, I can:
- Implement the full handshake KEM flow (controller encapsulate/decapsulate and worker encapsulate) once you confirm installing `pyOQS` in the devcontainer/CI is acceptable, or
- Prepare a PR that adds devcontainer Dockerfile steps to install liboqs so we can run the full integration here.
