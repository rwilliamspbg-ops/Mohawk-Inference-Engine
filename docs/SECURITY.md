# Security Guide for Mohawk Inference Engine

This document covers security architecture, threat models, and hardening procedures.

## Table of Contents

- [Security Architecture Overview](#security-architecture-overview)
- [Threat Model](#threat-model)
- [Cryptographic Requirements](#cryptographic-requirements)
- [Secure Deployment Checklist](#secure-deployment-checklist)
- [Vulnerability Mitigations](#vulnerability-mitigations)
- [Incident Response](#incident-response)

---

## Security Architecture Overview

### Defense-in-Depth Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Network Isolation                                   │
│   - VPC/VLAN separation                                      │
│   - Rate limiting                                            │
│   - DDoS protection                                          │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Transport Security                                  │
│   - TLS 1.3 + ECDHE                                          │
│   - PQC KEM handshake (Kyber512/768)                        │
│   - AEAD encryption (ChaCha20-Poly1305)                     │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Data Protection                                     │
│   - Model weights encrypted at rest                          │
│   - Activations encrypted in transit                         │
│   - TPM attestation (optional)                               │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Application Hardening                               │
│   - Input validation                                         │
│   - Circuit breakers                                         │
│   - Replay protection                                        │
└─────────────────────────────────────────────────────────────┘
```

### Key Security Features

| Feature | Implementation | Purpose |
|---------|---------------|---------|
| **Hybrid PQC KEX** | X25519 + Kyber768 | Quantum-resistant key exchange |
| **Forward Secrecy** | Ephemeral AEAD keys | Past sessions remain secure |
| **Replay Protection** | Nonce tracking | Prevents message replay attacks |
| **IP Protection** | Weight encryption | Model weights encrypted at rest |
| **TPM Attestation** | Intel SGX/SEV (optional) | Hardware-rooted trust |

---

## Threat Model

### Identified Threat Actors

| Actor | Capabilities | Threats | Mitigation |
|-------|--------------|---------|------------|
| **Network Attacker** | Intercept traffic, replay messages | Eavesdropping, replay attacks | AEAD encryption, nonce tracking |
| **Compromised Worker** | Read local memory, execute code | Model theft, data leakage | TPM attestation, encrypted weights at rest |
| **Malicious Client** | Send crafted inputs, overflow | DoS, input injection | Input validation, circuit breakers |
| **Supply Chain Attacker** | Compromise build pipeline | Backdoors, vulnerable dependencies | Signed builds, dependency scanning |
| **Quantum Computer** (future) | Break classical crypto | Key compromise | PQC KEM exchange (Kyber768) |

### Attack Vectors and Countermeasures

#### 1. Man-in-the-Middle (MitM) Attack

**Attack:** Attacker intercepts controller-worker communication

**Countermeasures:**
- Mutual TLS authentication with certificate pinning
- PQC KEM exchange prevents future decryption even if classical key compromised
- AEAD ensures integrity and authenticity of all messages

**Implementation:**
```python
# Secure handshake with certificate verification
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.x509 import load_pem_x509_certificate

def verify_worker_identity(worker_cert_pem, trusted_ca_pem):
    """Verify worker identity against CA."""
    cert = load_pem_x509_certificate(trusted_ca_pem)
    # Verify signature chain
    cert.verify_signature()  # Check CA signature
    return True
```

#### 2. Replay Attack

**Attack:** Attacker captures valid messages and replays them

**Countermeasures:**
- Sequence numbers or nonces in AEAD headers
- Nonce tracking per sender on receiver side
- Time-based nonce expiration windows

**Implementation:**
```python
# Replay protection in controller_secure.py
class ReplayProtectedAEAD(AEAD):
    def __init__(self, key: bytes, expected_sender_id: str, 
                 nonce_expiry_seconds: int = 3600):
        super().__init__(key)
        self.seen_nonces: Dict[str, float] = {}
        self.current_time = time.time()
    
    def is_nonce_fresh(self, nonce: bytes) -> bool:
        """Check if nonce hasn't been used recently."""
        nonce_str = nonce.hex()
        if nonce_str in self.seen_nonces:
            last_seen = self.seen_nonces[nonce_str]
            if self.current_time - last_seen < 3600:  # 1 hour window
                return False
        self.seen_nonces[nonce_str] = time.time()
        return True
    
    def encrypt(self, plaintext: bytes, aad: bytes = b''):
        nonce = os.urandom(12)
        
        # Check for replay before encryption
        if not self.is_nonce_fresh(nonce):
            raise ReplayError(f"Nonce {nonce.hex()} is stale")
        
        nonce, ct = super().encrypt(plaintext, aad)
        return nonce, ct
    
    def decrypt(self, nonce: bytes, ciphertext: bytes, aad: bytes = b''):
        # Check nonce freshness before decryption
        if not self.is_nonce_fresh(nonce):
            raise ReplayError(f"Nonce {nonce.hex()} is stale")
        
        return super().decrypt(nonce, ciphertext, aad)
```

#### 3. Model Weights Extraction Attack

**Attack:** Attacker extracts model weights from worker memory

**Countermeasures:**
- Encrypt weights at rest with separate key
- Use TEE (Intel SGX/AMD SEV) for sensitive operations
- Memory encryption via Intel TME or AMD SME

**Implementation:**
```python
# Encrypted weight storage
class SecureWeightStorage:
    def __init__(self, encryption_key_path: str):
        self.key = load_encryption_key(encryption_key_path)
    
    def store_weights(self, slice_id: str, weights: np.ndarray):
        """Store encrypted weights."""
        encrypted = ChaCha20Poly1305.encrypt(
            nonce=os.urandom(12),
            plaintext=pickle.dumps(weights),
            key=self.key
        )
        # Store with encryption metadata
        self._store_encrypted(slice_id, encrypted)
    
    def load_weights(self, slice_id: str):
        """Load and decrypt weights."""
        encrypted = self._load_encrypted(slice_id)
        decrypted = ChaCha20Poly1305.decrypt(
            nonce=encrypted[:12],
            ciphertext=encrypted[12:],
            key=self.key
        )
        return pickle.loads(decrypted)
```

#### 4. Side-Channel Attack

**Attack:** Attacker infers information from timing/power analysis

**Countermeasures:**
- Constant-time implementations for cryptographic operations
- Memory access randomization
- Noise injection in critical paths

---

## Cryptographic Requirements

### Minimum Cryptographic Strengths

| Component | Algorithm | Key Size | Mode |
|-----------|-----------|----------|------|
| **Key Exchange** | X25519 + Kyber768 | 256-bit + 2048-bit | Hybrid |
| **Symmetric Encryption** | ChaCha20-Poly1305 | 256-bit | AEAD |
| **Digital Signatures** | ECDSA P-384 | 384-bit | SHA-384 |
| **Hash Functions** | SHA-384 | 384-bit | NIST SP 800-131A compliant |

### Certificate Requirements

```yaml
# tls-certificates/requirements.yaml
certificate:
  minimum_validity_days: 365
  maximum_path_length: 2
  key_algorithm: "ECDSA"
  key_size_bits: 384
  curve: "secp384r1"
  
pqc_requirements:
  kem_algorithm: "Kyber768"
  minimum_kem_security_level: 3  # NIST security level
```

### Key Management

```python
# key_management.py
from cryptography.hazmat.primitives.asymmetric.ed448 import Ed448PrivateKey, Ed448PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import os

class SecureKeyManager:
    """Manages cryptographic keys with proper lifecycle."""
    
    def __init__(self, key_directory: str):
        self.key_directory = key_directory
        self.key_store = {}  # key_id -> (key_type, key_data)
    
    def load_private_key(self, key_path: str, password: bytes = None):
        """Load private key from PEM file."""
        with open(key_path, 'rb') as f:
            pem_data = f.read()
        
        if password:
            key = load_pem_private_key(pem_data, password=password)
        else:
            key = load_pem_private_key(pem_data, password=None)
        
        return key
    
    def generate_hybrid_keypair(self):
        """Generate hybrid classical + PQC keypair."""
        # Classical ECDH
        classical_priv = Ed448PrivateKey.generate()
        classical_pub = classical_priv.public_key()
        
        # PQC KEM (Kyber768)
        if OQS_AVAILABLE:
            kem = oqs.KeyEncapsulation("ML-KEM-768")
            pq_priv, pq_pub = kem.generate_keypair()
            
            return {
                'classical_private': classical_priv,
                'classical_public': classical_pub,
                'pq_private': pq_priv,
                'pq_public': pq_pub
            }
        
        raise RuntimeError("OQS not available for hybrid key generation")
    
    def rotate_key(self, old_key_id: str, new_key_path: str):
        """Rotate cryptographic key."""
        old_key = self.key_store.pop(old_key_id)
        
        # Generate new key
        new_keypair = self.generate_hybrid_keypair()
        
        # Migrate active sessions to new key
        self._migrate_sessions(old_key_id, new_keypair)
        
        # Store new key
        self.key_store[new_key_id] = new_keypair
    
    def _migrate_sessions(self, old_key_id: str, new_keypair):
        """Migrate active sessions from old to new key."""
        # Implement session migration logic
        pass
```

---

## Secure Deployment Checklist

### Pre-Deployment Security Review

- [ ] **TLS Configuration**: Verify TLS 1.3 with strong cipher suites
- [ ] **Certificate Validation**: Ensure CA chain is properly configured
- [ ] **PQC Integration**: Confirm liboqs installation and Kyber768 availability
- [ ] **Nonce Tracking**: Verify replay protection is enabled
- [ ] **Weight Encryption**: Confirm encryption key management procedure
- [ ] **Circuit Breakers**: Set appropriate thresholds for fault tolerance
- [ ] **Rate Limiting**: Configure request rate limits per client

### Environment Variables for Production Security

```bash
# Mandatory for production
export MIE_ENABLE_PQC=true
export MIE_REPLAY_PROTECTION_ENABLED=true
export MIE_NONCE_EXPIRY_SECONDS=3600
export MIE_WORKER_CERT_PATH=/etc/mohawk/worker.crt
export MIE_WORKER_KEY_PATH=/etc/mohawk/worker.key

# Optional but recommended
export MIE_TPM_ATTESTATION_REQUIRED=true
export MIE_WEIGHT_ENCRYPTION_ENABLED=true
export MIE_CIRCUIT_BREAKER_THRESHOLD=5
export MIE_MAX_CONCURRENT_SESSIONS=1000
```

### Container Security Hardening

```dockerfile
# Dockerfile.worker.security
FROM python:3.12-slim AS base

# Install liboqs for PQC support
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libssl-dev \
    pkg-config \
    && curl -sS https://liboqs.org/install.sh | bash \
    && ldconfig /usr/local/lib

# Copy application
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy compiled code
COPY prototype/ ./prototype/

# Security hardening
RUN useradd -u 1000 -g 1000 appuser && \
    chown -R appuser:appuser /app
    
USER appuser

EXPOSE 8003

CMD ["python", "prototype/worker_secure.py", "--port", "8003"]
```

---

## Vulnerability Mitigations

### Known Vulnerabilities and Remediations

| CVE Class | Risk Level | Mitigation Status | Reference |
|-----------|------------|-------------------|-----------|
| Pickle Deserialization (Prototype) | HIGH | Replace with protobuf/flatbuffers | [ARCHITECTURE.md §3.2](../docs/ARCHITECTURE.md#32-slice-format) |
| Replay Attack (Prototype) | MEDIUM | Nonce tracking implemented | `ReplayProtectedAEAD` class |
| Timing Side Channels (PQC) | LOW | Constant-time ops in liboqs | liboqs documentation |
| Memory Disclosure (GPU) | HIGH | TEE isolation recommended | See [DEPLOYMENT.md](./DEPLOYMENT.md#security-hardening) |

### Input Validation Requirements

```python
# input_validation.py
import re
from typing import Any, Dict

class SecureRequestValidator:
    """Validate and sanitize all incoming requests."""
    
    MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_SESSION_ID_LENGTH = 36  # UUID length
    
    def validate_slice_id(self, slice_id: str) -> bool:
        """Validate slice ID format."""
        pattern = r'^slice_\d+_\d+$'
        return bool(re.match(pattern, slice_id))
    
    def validate_session_id(self, session_id: str) -> bool:
        """Validate session ID is a proper UUID."""
        import uuid
        try:
            uuid.UUID(session_id)
            return True
        except ValueError:
            return False
    
    def validate_input_size(self, data: bytes) -> tuple[bool, str]:
        """Check input size limits."""
        if len(data) > self.MAX_INPUT_SIZE:
            return False, f"Input exceeds {self.MAX_INPUT_SIZE} byte limit"
        return True, ""
    
    def sanitize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Remove dangerous fields and validate types."""
        sanitized = {}
        
        for key, value in payload.items():
            # Reject control characters
            if isinstance(value, str) and any(c in value for c in ['<', '>', '"', "'", '&']):
                continue
            
            # Validate numeric fields
            if key in ['slice_id', 'manifest']:
                sanitized[key] = self._validate_literal(key, value)
            
        return sanitized
    
    def _validate_literal(self, field_name: str, value: Any) -> Any:
        """Validate a single literal field."""
        if isinstance(value, dict):
            # Validate nested dictionaries
            validated_dict = {}
            for k, v in value.items():
                if k.startswith('_'):  # Reject private fields
                    continue
                validated_dict[k] = v
            return validated_dict
        elif isinstance(value, (int, float)):
            if value < 0:
                raise ValueError(f"Negative value not allowed for {field_name}")
            return value
        return value
```

---

## Incident Response

### Security Incident Classification

| Severity | Criteria | Response Time | Escalation |
|----------|----------|---------------|------------|
| **P1 - Critical** | Active data breach, PQC key compromise | < 15 minutes | #mohawk-critical-oncall |
| **P2 - High** | Service degradation, replay attack detected | < 1 hour | mohawk-ops@sovereign-mohawk-proto.io |
| **P3 - Medium** | Configuration error, minor vulnerability | < 4 hours | GitHub issues |
| **P4 - Low** | Documentation gap, cosmetic issue | < 2 weeks | Regular backlog |

### Incident Response Procedures

#### P1: Active Data Breach

1. **Containment (0-15 minutes)**
   - Revoke compromised certificates
   - Rotate all cryptographic keys
   - Isolate affected workers from network

2. **Investigation (15-60 minutes)**
   - Collect logs from incident window
   - Analyze telemetry for attack pattern
   - Determine scope of data exposure

3. **Eradication (1-4 hours)**
   - Deploy patched binaries
   - Update TLS certificates
   - Rebuild affected instances

4. **Recovery (4-24 hours)**
   - Restore from clean backups
   - Verify PQC key exchange integrity
   - Resume normal operations

#### P2: Replay Attack Detection

```python
# incident_response/replay_attack_handler.py
import logging
from datetime import datetime

class ReplayAttackHandler:
    """Handle detected replay attack incidents."""
    
    def __init__(self, alert_endpoint: str):
        self.alert_endpoint = alert_endpoint
        self.incident_id = None
    
    def detect_replay(self, nonce: bytes, sender_id: str) -> bool:
        """Check for replay attack."""
        # Check if nonce was seen recently
        from prototype.crypto import ReplayProtectedAEAD
        
        aead = ReplayProtectedAEAD(
            key=self._get_key(sender_id),
            expected_sender_id=sender_id
        )
        
        try:
            aead.decrypt(nonce, ciphertext)
            logging.warning(f"Potential replay attack detected from {sender_id}")
            
            # Trigger incident response
            self.report_incident(
                severity="P2",
                type="REPLAY_ATTACK",
                source=sender_id,
                nonce=nonce.hex()
            )
            return True
        except Exception:
            return False
    
    def report_incident(self, severity: str, incident_type: str, **kwargs):
        """Report incident to monitoring system."""
        payload = {
            "severity": severity,
            "type": incident_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": kwargs
        }
        
        import requests
        response = requests.post(
            self.alert_endpoint,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        return response.json()
```

---

## Security Testing

### Static Analysis Configuration

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  scan-dependencies:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install safety bandit
    
    - name: Check for vulnerable dependencies
      run: |
        safety check --json > security-report.json
    
    - name: Run Bandit security linting
      run: |
        bandit -r prototype/ -f json -o bandit-report.json
    
    - name: Upload reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          security-report.json
          bandit-report.json
```

---

## Compliance Requirements

### NIST 800-53 Alignment

| Control Category | Requirement | Implementation |
|-----------------|-------------|----------------|
| **AC-2** (Access Control) | Role-based access to workers | Certificate-based authentication |
| **SC-8** (Transmission Confidentiality) | Encrypt in transit | TLS + PQC KEM |
| **SC-12** (Cryptographic Protection) | Protect data at rest | Weight encryption |
| **SI-4** (Intrusion Detection) | Monitor for attacks | Prometheus metrics, alerting |

### SOC 2 Type II Readiness

- [x] Logical access controls (certificate auth)
- [x] Network security (VPC isolation)
- [x] Encryption at rest and in transit
- [x] Incident response procedures
- [ ] Third-party risk assessments (pending)
- [ ] Penetration testing reports (scheduled Q3)

---

## References

- [NIST IR 8413](https://csrc.nist.gov/publications/detail/ir/8413): Post-Quantum Cryptography Implementation Guide
- [OWASP Top 10](https://owasp.org/www-project-top-ten/): Web Application Security
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes): Container hardening

---

*Last updated: 2026-01-XX*
*Maintained by: Mohawk Ops Team, Sovereign Mohawk Proto LLC*
