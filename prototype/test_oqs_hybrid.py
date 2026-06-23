import sys
import pytest
from prototype.crypto import PQCAdapter, derive_hybrid_key, AEAD, OQS_AVAILABLE


def test_oqs_hybrid_encap_decap():
    if not OQS_AVAILABLE:
        pytest.skip('oqs module not available')
    # create two adapters (controller and worker)
    c = PQCAdapter()
    w = PQCAdapter()
    # ensure both report oqs_supported; skip if pyOQS API not present
    if not getattr(c, 'oqs_supported', False) or not getattr(w, 'oqs_supported', False):
        pytest.skip('pyOQS KEM API not available in this environment')
    # exchange oqs public keys
    c_pub = c.get_oqs_public()
    w_pub = w.get_oqs_public()
    # controller encapsulates to worker's pub
    ct, ss_c = c.encap(w_pub)
    # worker decapsulates
    ss_w = w.decap(ct)
    assert ss_c == ss_w
    # also derive X25519 shared
    x_c = c.derive_shared(w.public_bytes())
    x_w = w.derive_shared(c.public_bytes())
    assert x_c == x_w
    # derive hybrid key and verify AEAD
    hybrid_c = derive_hybrid_key(x_c, ss_c)
    hybrid_w = derive_hybrid_key(x_w, ss_w)
    assert hybrid_c == hybrid_w
    aead = AEAD(hybrid_c)
    plaintext = b'test message'
    nonce, ct = aead.encrypt(plaintext)
    out = aead.decrypt(nonce, ct)
    assert out == plaintext
