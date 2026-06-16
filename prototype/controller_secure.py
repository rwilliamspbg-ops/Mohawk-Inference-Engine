import base64
import pickle
import random
import threading
import time

import requests

from prototype.crypto_improved import AEAD, PQCAdapter, ReplayProtectedAEAD, b64, ub64
from prototype.model_tools import ToyModel, WeightSlice


class SecureController:
    """
    Secure controller with replay-protected encryption.

    Uses ReplayProtectedAEAD for all encrypted communications to prevent replay attacks.
    """

    def __init__(self, workers):
        self.workers = workers
        self.keys = {}  # worker_url -> ReplayProtectedAEAD
        self.kems = {}  # worker_url -> PQCAdapter (ephemeral keypair reused per worker)
        self.kem_locks = {w: threading.Lock() for w in workers}

        # Attempt initial handshake with all workers
        for w in workers:
            try:
                self.handshake_with_worker(w)
            except Exception:
                # Don't fail construction; handshake will be attempted lazily
                pass

    def partition_model(self, model: ToyModel, num_slices: int = 2):
        """Partition model into balanced slices."""
        L = len(model.weights)
        slice_size = (L + num_slices - 1) // num_slices

        slices = []
        for i in range(num_slices):
            start = i * slice_size
            end = min(L, start + slice_size)

            if start >= L:
                break

            sub = model.slice(start, end)
            slices.append(sub)

        return slices

    def handshake_with_worker(self, worker_url):
        """
        Perform secure handshake with a worker.

        Uses ReplayProtectedAEAD for all subsequent encrypted communications.
        """
        if worker_url not in self.kem_locks:
            self.kem_locks[worker_url] = threading.Lock()

        lock = self.kem_locks[worker_url]
        with lock:
            # Reuse or create KEM per worker for stable shared key
            if worker_url in self.kems:
                kem = self.kems[worker_url]
            else:
                kem = PQCAdapter()
                self.kems[worker_url] = kem

            client_pub = kem.public_bytes()

            # Include optional OQS public bytes if available
            payload = {"client_pub_b64": b64(client_pub), "client_id": "controller"}

            try:
                oqs_pub = kem.get_oqs_public()
                if oqs_pub:
                    payload["oqs_pub_b64"] = b64(oqs_pub)
            except Exception:
                pass

            r = requests.post(f"{worker_url}/handshake", json=payload, timeout=5)
            r.raise_for_status()

            j = r.json()
            worker_pub_b64 = j["worker_pub_b64"]

            # Optional worker OQS pub and encapsulation ct for hybrid KEM
            worker_oqs_b64 = j.get("worker_oqs_pub_b64")
            worker_oqs_ct_b64 = j.get("worker_oqs_ct_b64")

            worker_pub = ub64(worker_pub_b64)
            x25519_shared = kem.derive_shared(worker_pub)

            # If worker returned an OQS encapsulation, decapsulate and derive hybrid key
            final_key = None

            if worker_oqs_ct_b64 and kem.oqs_supported:
                try:
                    ct = ub64(worker_oqs_ct_b64)
                    oqs_shared = kem.decap(ct)
                    from prototype.crypto_improved import derive_hybrid_key

                    final_key = derive_hybrid_key(x25519_shared, oqs_shared)
                except Exception:
                    final_key = x25519_shared
            else:
                final_key = x25519_shared

            # Use ReplayProtectedAEAD for all encrypted communications
            self.keys[worker_url] = ReplayProtectedAEAD(
                final_key, nonce_expiry_seconds=3600
            )

            return True

    def preload_slices(self, slices, encrypt=False):
        """Preload model slices to workers with optional encryption."""
        assigned = []

        for i, slice_obj in enumerate(slices):
            w = self.workers[i % len(self.workers)]
            blob = slice_obj.to_bytes()

            manifest = {"start": slice_obj.start_layer, "end": slice_obj.end_layer}
            slice_id = f"slice_{slice_obj.start_layer}_{slice_obj.end_layer}"

            if encrypt:
                # Ensure handshake is complete
                if w not in self.keys:
                    self.handshake_with_worker(w)

                aead = self.keys[w]
                nonce, ct = aead.encrypt(blob)

                payload = {
                    "slice_id": slice_id,
                    "manifest": manifest,
                    "encrypted": True,
                    "weights_b64": b64(ct),
                    "nonce_b64": b64(nonce),
                }
            else:
                payload = {
                    "slice_id": slice_id,
                    "manifest": manifest,
                    "weights_b64": b64(blob),
                }

            # Retry with exponential backoff for transient failures
            max_attempts = 3
            backoff_base = 0.1

            for attempt in range(1, max_attempts + 1):
                try:
                    r = requests.post(f"{w}/preload", json=payload, timeout=10)
                    r.raise_for_status()
                    break
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    sleep_t = backoff_base * (2 ** (attempt - 1)) + random.uniform(
                        0, backoff_base
                    )
                    time.sleep(sleep_t)

            assigned.append((slice_id, w))

        return assigned

    def run_distributed(self, assigned, x_blob, encrypt=False):
        """Run distributed inference with optional encryption."""
        current = x_blob

        for slice_id, w in assigned:
            if encrypt:
                aead = self.keys[w]
                nonce, ct = aead.encrypt(current)

                payload = {
                    "slice_id": slice_id,
                    "encrypted": True,
                    "input_b64": b64(ct),
                    "nonce_b64": b64(nonce),
                }

                # Retry execute with backoff for transient errors
                max_attempts = 3
                backoff_base = 0.1

                for attempt in range(1, max_attempts + 1):
                    try:
                        r = requests.post(f"{w}/execute", json=payload, timeout=30)
                        r.raise_for_status()
                        break
                    except Exception:
                        if attempt == max_attempts:
                            raise
                        sleep_t = backoff_base * (2 ** (attempt - 1))
                        time.sleep(sleep_t)
            else:
                payload = {
                    "slice_id": slice_id,
                    "input_b64": base64.b64encode(current).decode("ascii"),
                }

                # Non-encrypted execute also gets retries
                max_attempts = 3
                backoff_base = 0.1

                for attempt in range(1, max_attempts + 1):
                    try:
                        r = requests.post(f"{w}/execute", json=payload, timeout=30)
                        r.raise_for_status()
                        break
                    except Exception:
                        if attempt == max_attempts:
                            raise
                        sleep_t = backoff_base * (2 ** (attempt - 1))
                        time.sleep(sleep_t)

            r.raise_for_status()
            j = r.json()

            if j.get("encrypted"):
                aead = self.keys[w]
                nonce = ub64(j["nonce_b64"])
                ct = ub64(j["output_b64"])
                out = aead.decrypt(nonce, ct)
                current = out
            else:
                out_b64 = j["output_b64"]
                current = base64.b64decode(out_b64)

        return current
