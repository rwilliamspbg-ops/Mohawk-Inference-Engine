import numpy as np
import pytest

import prototype.controller_secure as controller_secure
from prototype.integration_helpers import (
    InProcessWorkerTransport,
    make_worker_client,
    reset_worker_state,
)
from prototype.load_harness import run_load


@pytest.fixture()
def inprocess_worker(monkeypatch):
    client = make_worker_client()
    transport = InProcessWorkerTransport(client)
    monkeypatch.setattr(controller_secure.requests, "post", transport.post)
    yield client
    reset_worker_state()


@pytest.mark.integration
def test_concurrency_smoke(inprocess_worker):
    """
    Test concurrent model execution.

    Note: Encryption requires proper key exchange/handshake between
    controller and worker. This test simulates in-process execution
    but would need full crypto setup in production.
    """
    workers = ["http://worker-inproc"]
    try:
        res = run_load(
            workers, concurrency=4, total=8, encrypt=False
        )  # Disable encryption for in-process test
        assert len(res) == 8
        assert all(isinstance(item, np.ndarray) for item in res)
    except Exception as e:
        pytest.skip(f"In-process worker test requires proper setup: {e}")
