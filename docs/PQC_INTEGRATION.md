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
     
     # Install the Python bindings that import as `oqs`
     pip install liboqs-python
     ```
   - Alternatively use your distribution's packages or a prepared devcontainer that installs liboqs.
   - Set `OQS_INSTALL_PATH=/usr/local` when using a local source install so the binding can find the shared library.

2. Update `prototype/crypto.py` to perform a proper KEM exchange during handshake:
   - Controller: send X25519 pub + OQS pub to worker.
   - Worker: encapsulate to controller's OQS pub -> return encapsulation ciphertext + worker OQS pub.
   - Controller: decapsulate ciphertext to obtain OQS shared secret.
   - Final symmetric AEAD key = HKDF(X25519_shared || OQS_shared)
   - The current binding in this workspace exposes `oqs.KeyEncapsulation`, `generate_keypair()`, `encap_secret()`, and `decap_secret()`.

3. Tests & validation:
   - Run `pytest -q prototype/test_oqs_hybrid.py prototype/test_secure_hybrid_integration.py prototype/test_concurrency_smoke.py`.
   - Use `prototype/test_secure_run.py` as a quick smoke script when you want a single-session end-to-end check.
   - Ensure the worker `/handshake` returns `worker_oqs_pub_b64` and `worker_pub_b64` when liboqs is available.

Notes:
- The repository already contains scaffolding in `prototype/crypto.py` to detect pyOQS at runtime and expose `get_oqs_public()`; complete integration requires invoking `kem.encapsulate()` and `kem.decapsulate()` where appropriate.
- Building liboqs on CI requires adding native build steps in the pipeline; consider a GitHub Actions matrix job with a prebuilt liboqs artifact or using a self-hosted runner.
- The CI workflow includes a manual `workflow_dispatch` trigger that can build liboqs from source when `build_liboqs` is enabled.

If you want, I can:
- Implement the full handshake KEM flow (controller encapsulate/decapsulate and worker encapsulate) once you confirm installing `pyOQS` in the devcontainer/CI is acceptable, or
- Prepare a PR that adds devcontainer Dockerfile steps to install liboqs so we can run the full integration here.
