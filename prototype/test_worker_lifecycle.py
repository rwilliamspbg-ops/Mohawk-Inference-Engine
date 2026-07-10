import numpy as np
import pytest

import prototype.controller_secure as controller_secure
from prototype.integration_helpers import (
    InProcessWorkerTransport,
    make_worker_client,
    reset_worker_state,
)
from prototype.model_tools import ToyModel
from prototype.session_manager import SessionManager

@pytest.fixture()
def inprocess_worker(monkeypatch):
    client = make_worker_client()
    transport = InProcessWorkerTransport(client)
    monkeypatch.setattr(controller_secure.requests, "post", transport.post)
    yield client
    reset_worker_state()

def test_worker_leave_triggers_slice_reshare_without_errors(inprocess_worker):
    workers = ["http://worker-a", "http://worker-b"]
    sm = SessionManager(workers)

    model = ToyModel([8, 16, 16, 8], seed=42)
    x = np.random.default_rng(17).standard_normal((8, 1)).astype("float32")
    baseline = model.forward(x)

    sid = sm.start_session(model, num_slices=2, encrypt=False)

    # Remove a worker that was part of the initial assignment.
    sm.leave_worker("http://worker-a")

    out = sm.infer(sid, x)
    sm.end_session(sid)

    assert np.allclose(out, baseline)

def test_worker_join_leave_reconnect_encrypted_flow(inprocess_worker):
    workers = ["http://worker-a"]
    sm = SessionManager(workers)

    model = ToyModel([8, 16, 16, 8], seed=42)
    x = np.random.default_rng(29).standard_normal((8, 1)).astype("float32")
    baseline = model.forward(x)

    sid = sm.start_session(model, num_slices=2, encrypt=True)

    # Simulate join/leave transition and ensure encrypted execution keeps working.
    sm.join_worker("http://worker-b", handshake=True)
    sm.leave_worker("http://worker-a")

    out_after_leave = sm.infer(sid, x)
    assert np.allclose(out_after_leave, baseline)

    # Reconnect original worker and verify no errors on subsequent runs.
    assert sm.reconnect_worker("http://worker-a") is True
    out_after_reconnect = sm.infer(sid, x)
    sm.end_session(sid)

    assert np.allclose(out_after_reconnect, baseline)
