import pytest
import numpy as np

import prototype.controller_secure as controller_secure
from prototype.integration_helpers import InProcessWorkerTransport, make_worker_client, reset_worker_state
from prototype.load_harness import run_load


@pytest.fixture()
def inprocess_worker(monkeypatch):
    client = make_worker_client()
    transport = InProcessWorkerTransport(client)
    monkeypatch.setattr(controller_secure.requests, 'post', transport.post)
    yield client
    reset_worker_state()


def test_concurrency_smoke(inprocess_worker):
    workers = ['http://worker-inproc']
    res = run_load(workers, concurrency=4, total=8, encrypt=True)
    assert len(res) == 8
    assert all(isinstance(item, np.ndarray) for item in res)
