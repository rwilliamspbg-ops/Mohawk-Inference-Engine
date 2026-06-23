from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import os
import base64
from cryptography.hazmat.primitives import serialization

# Try to detect liboqs / pyOQS availability. If present, we'll expose
# scaffolding for a PQC KEM; if not present, we gracefully fall back
# to the existing X25519-only DH flow.
OQS_AVAILABLE = False
_oqs = None
try:
    import oqs as _oqs  # type: ignore
    OQS_AVAILABLE = True
except Exception:
    OQS_AVAILABLE = False


class PQCAdapter:
    """Hybrid PQC adapter scaffold.

    Current behaviour:
    - Always performs an X25519 DH exchange to produce a shared secret.
    - If liboqs/pyOQS is present on both peers, this class exposes
      additional public bytes fields so a real KEM exchange can be
      implemented later without changing the outer handshake shape.

    Note: proper KEM encapsulate/decapsulate requires extra ciphertext
    to be exchanged. This file adds scaffolding so that future work can
    implement a full liboqs hybrid KEM without large protocol changes.
    """

    def __init__(self, oqs_alg: str = 'Kyber512'):
        self._priv = x25519.X25519PrivateKey.generate()
        self.pub = self._priv.public_key()
        self.oqs_supported = False
        self.oqs_alg = oqs_alg
        self.oqs_public = b''
        if OQS_AVAILABLE:
            try:
                kem_cls = getattr(_oqs, 'KeyEncapsulation', None)
                if kem_cls is None:
                    kem_cls = getattr(_oqs, 'KEM', None)
                if kem_cls is None:
                    raise RuntimeError('No OQS KEM class available')
                self.kem = kem_cls(self.oqs_alg)
                pub = self.kem.generate_keypair()
                if isinstance(pub, tuple):
                    pub = pub[0]
                self.oqs_public = pub
                self.oqs_supported = True
            except Exception:
                self.kem = None
                self.oqs_public = b''
                self.oqs_supported = False

    def public_bytes(self) -> bytes:
        """Return the X25519 public bytes. For forward-compatibility we
        also expose an optional OQS public blob via `get_oqs_public()`.
        The current handshake uses only the X25519 bytes for key
        derivation; OQS support is scaffolding for later hybrid KEM
        steps.
        """
        return self.pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def get_oqs_public(self) -> bytes:
        return self.oqs_public

    def derive_shared(self, peer_public_bytes: bytes) -> bytes:
        """Derive a symmetric AEAD key. Currently this uses X25519 DH
        only (keeps existing behaviour). When OQS hybrid KEM is fully
        implemented, concat/PRF of both secrets should be used here.
        """
        peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared = self._priv.exchange(peer_pub)
        # derive AEAD key from shared secret
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'mohawk-aead-key',
        )
        key = hkdf.derive(shared)
        return key

    # OQS helper wrappers: encapsulate/decapsulate when available
    def encap(self, peer_oqs_pub: bytes):
        """Encapsulate to `peer_oqs_pub` using the pyOQS KEM if available.
        Returns (ct, shared) or raises RuntimeError if not supported.
        """
        if not self.oqs_supported or not getattr(self, 'kem', None):
            raise RuntimeError('OQS not available')
        # Try common pyOQS method names defensively
        try:
            # pyOQS KeyEncapsulation API: kem.encap_secret(pub) or kem.encapsulate(pub)
            if hasattr(self.kem, 'encap_secret'):
                ct, ss = self.kem.encap_secret(peer_oqs_pub)
                return ct, ss
            if hasattr(self.kem, 'encapsulate'):
                ct, ss = self.kem.encapsulate(peer_oqs_pub)
                return ct, ss
            if hasattr(self.kem, 'encap'):
                ct, ss = self.kem.encap(peer_oqs_pub)
                return ct, ss
        except Exception as e:
            raise RuntimeError('OQS encapsulation failed: %s' % e)
        raise RuntimeError('OQS encapsulation not supported by this pyOQS build')

    def decap(self, ct: bytes):
        """Decapsulate ciphertext `ct` using stored private key. Returns shared secret."""
        if not self.oqs_supported or not getattr(self, 'kem', None):
            raise RuntimeError('OQS not available')
        try:
            if hasattr(self.kem, 'decap_secret'):
                ss = self.kem.decap_secret(ct)
                return ss
            if hasattr(self.kem, 'decapsulate'):
                ss = self.kem.decapsulate(ct)
                return ss
            if hasattr(self.kem, 'decap'):
                ss = self.kem.decap(ct)
                return ss
        except Exception as e:
            raise RuntimeError('OQS decapsulation failed: %s' % e)
        raise RuntimeError('OQS decapsulation not supported by this pyOQS build')


def derive_hybrid_key(shared_x25519: bytes, shared_oqs: bytes) -> bytes:
    """Derive a single AEAD key from two raw shared secrets (concatenate
    and run HKDF). This produces a 32-byte AEAD key.
    """
    combined = (shared_x25519 or b'') + (shared_oqs or b'')
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'mohawk-hybrid-aead-key',
    )
    return hkdf.derive(combined)


class AEAD:
    def __init__(self, key: bytes):
        self.key = key
        self.aead = ChaCha20Poly1305(key)

    def encrypt(self, plaintext: bytes, aad: bytes = b''):
        nonce = os.urandom(12)
        ct = self.aead.encrypt(nonce, plaintext, aad)
        return nonce, ct

    def decrypt(self, nonce: bytes, ciphertext: bytes, aad: bytes = b''):
        return self.aead.decrypt(nonce, ciphertext, aad)


# helpers
def b64(x: bytes) -> str:
    return base64.b64encode(x).decode('ascii')


def ub64(s: str) -> bytes:
    return base64.b64decode(s)
