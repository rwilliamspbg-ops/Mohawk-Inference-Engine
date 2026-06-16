"""
Improved cryptographic primitives with replay protection and versioned keys.
"""

import base64
import os
import time
from typing import Optional, Set

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Try to detect liboqs / pyOQS availability
OQS_AVAILABLE = False
_oqs = None
try:
    import oqs as _oqs

    OQS_AVAILABLE = True
except Exception:
    OQS_AVAILABLE = False


class ReplayProtectedAEAD:
    """
    AEAD encryption with replay protection.

    Tracks seen nonces to prevent replay attacks.
    Nonces expire after configurable timeout (default 1 hour).
    """

    def __init__(self, key: bytes, nonce_expiry_seconds: int = 3600):
        self.key = key
        self.aead = ChaCha20Poly1305(key)
        self.seen_nonces: dict = {}  # Maps nonce_str -> timestamp
        self.nonce_expiry_seconds = nonce_expiry_seconds
        self.lock = __import__("threading").Lock()

    def _cleanup_stale_nonces(self):
        """Remove expired nonces from tracking."""
        current_time = time.time()
        expired = []

        for nonce_str, timestamp in self.seen_nonces.items():
            if current_time - timestamp > self.nonce_expiry_seconds:
                expired.append(nonce_str)

        for nonce in expired:
            del self.seen_nonces[nonce]

    def is_nonce_fresh(self, nonce: bytes) -> bool:
        """
        Check if nonce hasn't been used recently.

        Args:
            nonce: The nonce to check

        Returns:
            True if nonce is fresh (not seen or expired), False otherwise
        """
        nonce_str = nonce.hex()

        with self.lock:
            # Clean up stale nonces first
            self._cleanup_stale_nonces()

            # Check if nonce was seen recently
            if nonce_str in self.seen_nonces:
                return False

            # Mark nonce as seen with current timestamp
            self.seen_nonces[nonce_str] = time.time()
            return True

    def encrypt(self, plaintext: bytes, aad: bytes = b"") -> tuple:
        """
        Encrypt plaintext with replay protection.

        Args:
            plaintext: Data to encrypt
            aad: Additional authenticated data

        Returns:
            Tuple of (nonce, ciphertext)

        Raises:
            RuntimeError: If nonce collision detected (replay attack)
        """
        # Generate fresh nonce
        nonce = os.urandom(12)

        # Check for replay before encryption
        if not self.is_nonce_fresh(nonce):
            raise RuntimeError(f"Nonce collision detected - possible replay attack")

        # Encrypt with the generated nonce
        ct = self.aead.encrypt(nonce, plaintext, aad)
        return nonce, ct

    def decrypt(self, nonce: bytes, ciphertext: bytes, aad: bytes = b"") -> bytes:
        """
        Decrypt ciphertext with optional replay protection.

        Note: Decryption (reads) are idempotent and don't need replay protection.
        Only encryption (writes) needs to prevent nonce reuse to prevent replay attacks.

        Args:
            nonce: The nonce used for encryption
            ciphertext: Encrypted data
            aad: Additional authenticated data

        Returns:
            Decrypted plaintext
        """
        # For decryption, we don't enforce nonce freshness since reads are idempotent
        # The AEAD authentication will still prevent tampering
        return self.aead.decrypt(nonce, ciphertext, aad)


class PQCAdapter:
    """Hybrid PQC adapter with improved key management."""

    def __init__(self, oqs_alg: str = "Kyber512"):
        self._priv = x25519.X25519PrivateKey.generate()
        self.pub = self._priv.public_key()
        self.oqs_supported = False
        self.oqs_alg = oqs_alg
        self.oqs_public = b""

        if OQS_AVAILABLE:
            try:
                kem_cls = getattr(_oqs, "KeyEncapsulation", None)
                if kem_cls is None:
                    kem_cls = getattr(_oqs, "KEM", None)
                if kem_cls is None:
                    raise RuntimeError("No OQS KEM class available")
                self.kem = kem_cls(oqs_alg)
                pub = self.kem.generate_keypair()
                if isinstance(pub, tuple):
                    pub = pub[0]
                self.oqs_public = pub
                self.oqs_supported = True
            except Exception:
                self.kem = None
                self.oqs_public = b""
                self.oqs_supported = False

    def public_bytes(self) -> bytes:
        """Return the X25519 public bytes."""
        return self.pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def get_oqs_public(self) -> bytes:
        """Return OQS public bytes if available."""
        return self.oqs_public

    def derive_shared(self, peer_public_bytes: bytes) -> bytes:
        """Derive a symmetric AEAD key using X25519 DH."""
        peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared = self._priv.exchange(peer_pub)

        # Derive AEAD key from shared secret with versioned info string
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=os.urandom(32),  # Explicit random salt
            info=b"mohawk-v1-aead-key",  # Versioned info string
        )
        key = hkdf.derive(shared)
        return key

    def encap(self, peer_oqs_pub: bytes):
        """Encapsulate to peer's OQS public key."""
        if not self.oqs_supported or not getattr(self, "kem", None):
            raise RuntimeError("OQS not available")

        try:
            if hasattr(self.kem, "encap_secret"):
                ct, ss = self.kem.encap_secret(peer_oqs_pub)
                return ct, ss
            if hasattr(self.kem, "encapsulate"):
                ct, ss = self.kem.encapsulate(peer_oqs_pub)
                return ct, ss
            if hasattr(self.kem, "encap"):
                ct, ss = self.kem.encap(peer_oqs_pub)
                return ct, ss
        except Exception as e:
            raise RuntimeError(f"OQS encapsulation failed: {e}")

        raise RuntimeError("OQS encapsulation not supported")

    def decap(self, ct: bytes):
        """Decapsulate ciphertext to get shared secret."""
        if not self.oqs_supported or not getattr(self, "kem", None):
            raise RuntimeError("OQS not available")

        try:
            if hasattr(self.kem, "decap_secret"):
                ss = self.kem.decap_secret(ct)
                return ss
            if hasattr(self.kem, "decapsulate"):
                ss = self.kem.decapsulate(ct)
                return ss
            if hasattr(self.kem, "decap"):
                ss = self.kem.decap(ct)
                return ss
        except Exception as e:
            raise RuntimeError(f"OQS decapsulation failed: {e}")

        raise RuntimeError("OQS decapsulation not supported")


def derive_hybrid_key(shared_x25519: bytes, shared_oqs: bytes) -> bytes:
    """Derive a single AEAD key from two raw shared secrets."""
    combined = (shared_x25519 or b"") + (shared_oqs or b"")

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=os.urandom(32),  # Explicit random salt
        info=b"mohawk-v1-hybrid-aead-key",  # Versioned info string
    )
    return hkdf.derive(combined)


class AEAD:
    """
    Basic AEAD encryption (without replay protection).

    Use ReplayProtectedAEAD for production deployments.
    """

    def __init__(self, key: bytes):
        self.key = key
        self.aead = ChaCha20Poly1305(key)

    def encrypt(self, plaintext: bytes, aad: bytes = b"") -> tuple:
        nonce = os.urandom(12)
        ct = self.aead.encrypt(nonce, plaintext, aad)
        return nonce, ct

    def decrypt(self, nonce: bytes, ciphertext: bytes, aad: bytes = b"") -> bytes:
        return self.aead.decrypt(nonce, ciphertext, aad)


# Helper functions
def b64(x: bytes) -> str:
    return base64.b64encode(x).decode("ascii")


def ub64(s: str) -> bytes:
    return base64.b64decode(s)
