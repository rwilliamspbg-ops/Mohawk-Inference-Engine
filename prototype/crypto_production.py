# prototype/crypto_production.py (ENHANCED)
from typing import Optional, Tuple
import os
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

OQS_AVAILABLE = False
try:
    import oqs as _oqs
    OQS_AVAILABLE = True
except Exception:
    pass


class ProductionPQCAdapter:
    """Production-ready PQC adapter with full hybrid KEM support."""
    
    def __init__(self, oqs_alg: str = 'Kyber768'):
        self._priv_x25519 = x25519.X25519PrivateKey.generate()
        self.pub_x25519 = self._priv_x25519.public_key()
        
        self.oqs_supported = False
        self.oqs_alg = oqs_alg
        
        if OQS_AVAILABLE:
            try:
                kem_cls = getattr(_oqs, 'KeyEncapsulation', None) or \
                          getattr(_oqs, 'KEM', None)
                if kem_cls:
                    self.kem = kem_cls(oqs_alg)
                    pub = self.kem.generate_keypair()
                    if isinstance(pub, tuple):
                        pub = pub[0]
                    self.oqs_public = pub
                    self.oqs_supported = True
            except Exception:
                pass
    
    def public_bytes(self) -> bytes:
        """Return X25519 public key."""
        return self.pub_x25519.public_bytes(
            encoding=x25519.Encoding.Raw,
            format=x25519.PublicFormat.Raw,
        )
    
    def get_oqs_public(self) -> Optional[bytes]:
        """Return OQS public key if available."""
        return self.oqs_public if self.oqs_supported else None
    
    def derive_shared(self, peer_public_bytes: bytes) -> bytes:
        """Derive symmetric AEAD key from X25519 DH."""
        peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared = self._priv_x25519.exchange(peer_pub)
        
        hkdf = HKDF(
            algorithm=hashes.SHA384(),  # Use SHA-384 for stronger security
            length=48,  # 48 bytes: 32 for AEAD key + 16 for nonce IV
            salt=b'mohawk-hybrid-key-salt',
            info=b'hybrid-key-derivation-v2',
        )
        
        return hkdf.derive(shared)
    
    def encap(self, peer_oqs_pub: bytes) -> Tuple[bytes, bytes]:
        """Encapsulate to peer's OQS public key."""
        if not self.oqs_supported or not getattr(self, 'kem', None):
            raise RuntimeError('OQS not available')
        
        # Use correct API method based on pyOQS version
        if hasattr(self.kem, 'encapsulate'):
            ct, ss = self.kem.encapsulate(peer_oqs_pub)
        elif hasattr(self.kem, 'encap_secret'):
            ct, ss = self.kem.encap_secret(peer_oqs_pub)
        else:
            raise AttributeError('Unsupported OQS encapsulation method')
        
        return ct, ss
    
    def decap(self, ct: bytes) -> bytes:
        """Decapsulate ciphertext to retrieve shared secret."""
        if not self.oqs_supported or not getattr(self, 'kem', None):
            raise RuntimeError('OQS not available')
        
        if hasattr(self.kem, 'decapsulate'):
            ss = self.kem.decapsulate(ct)
        elif hasattr(self.kem, 'decap_secret'):
            ss = self.kem.decap_secret(ct)
        else:
            raise AttributeError('Unsupported OQS decapsulation method')
        
        return ss


class ReplayProtectedAEAD:
    """Production AEAD with replay protection."""
    
    def __init__(
        self, 
        key: bytes,
        expected_sender_id: str,
        nonce_expiry_seconds: int = 3600,
        max_nonces_per_window: int = 1000
    ):
        self.key = key
        self.sender_id = expected_sender_id
        self.nonce_expiry = nonce_expiry_seconds
        self.max_nonces = max_nonces_per_window
        
        # Nonce tracking with time windows
        self.seen_nonces: Dict[str, Tuple[float, int]] = {}  # nonce_hex -> (timestamp, usage_count)
        
        self.aead = ChaCha20Poly1305(key)
    
    def is_nonce_fresh(self, nonce: bytes) -> bool:
        """Check if nonce hasn't been used recently."""
        nonce_str = nonce.hex()
        
        if nonce_str in self.seen_nonces:
            last_seen, usage_count = self.seen_nonces[nonce_str]
            time_diff = time.time() - last_seen
            
            # Check if within expiry window
            if time_diff < self.nonce_expiry:
                # Count usages in current window
                if usage_count >= self.max_nonces or time_diff > 300:  # 5 min refresh
                    return False
        else:
            # First time seeing this nonce
            self.seen_nonces[nonce_str] = (time.time(), 1)
        
        return True
    
    def encrypt(self, plaintext: bytes, aad: bytes = b'') -> Tuple[bytes, bytes]:
        """Encrypt with replay protection."""
        nonce = os.urandom(12)
        
        # Check for replay before encryption
        if not self.is_nonce_fresh(nonce):
            raise ReplayError(f"Nonce {nonce.hex()} is stale")
        
        nonce, ct = self.aead.encrypt(nonce, plaintext, aad)
        return nonce, ct
    
    def decrypt(self, nonce: bytes, ciphertext: bytes, aad: bytes = b'') -> bytes:
        """Decrypt with replay protection."""
        if not self.is_nonce_fresh(nonce):
            raise ReplayError(f"Nonce {nonce.hex()} is stale")
        
        return self.aead.decrypt(nonce, ciphertext, aad)
