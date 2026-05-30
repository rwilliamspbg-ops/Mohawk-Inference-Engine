import numpy as np
import pytest

from prototype.crypto import OQS_AVAILABLE, PQCAdapter
from prototype.integration_helpers import InProcessWorkerTransport, make_worker_client, reset_worker_state
from prototype.model_tools import ToyModel
from prototype.session_manager import SessionManager
import prototype.controller_secure as controller_secure


def _hybrid_supported() -> bool:
    return OQS_AVAILABLE and PQCAdapter().oqs_supported


@pytest.fixture()
def inprocess_worker(monkeypatch):
    client = make_worker_client()
    transport = InProcessWorkerTransport(client)
    monkeypatch.setattr(controller_secure.requests, 'post', transport.post)
    yield client
    reset_worker_state()


def test_secure_hybrid_roundtrip_inprocess(inprocess_worker):
    if not _hybrid_supported():
        pytest.skip('pyOQS hybrid KEM not available in this environment')

    workers = ['http://worker-inproc']
    sm = SessionManager(workers)
    model = ToyModel([8, 16, 16, 8], seed=42)
    x = np.random.default_rng(7).standard_normal((8, 1)).astype('float32')

    sid = sm.start_session(model, num_slices=2, encrypt=True)
    out = sm.infer(sid, x)
    sm.end_session(sid)

    baseline = model.forward(x)
    assert np.allclose(out, baseline)
