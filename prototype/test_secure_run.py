import numpy as np
import pytest

import prototype.controller_secure as controller_secure
from prototype.integration_helpers import InProcessWorkerTransport, make_worker_client, reset_worker_state
from prototype.model_tools import ToyModel
from prototype.session_manager import SessionManager


@pytest.fixture()
def inprocess_worker(monkeypatch):
	client = make_worker_client()
	transport = InProcessWorkerTransport(client)
	monkeypatch.setattr(controller_secure.requests, 'post', transport.post)
	yield client
	reset_worker_state()


def test_secure_run_roundtrip_inprocess(inprocess_worker):
	workers = ['http://worker-inproc']
	sm = SessionManager(workers)
	model = ToyModel([8, 16, 16, 8], seed=42)

	x = np.random.default_rng(1).standard_normal((8, 1)).astype('float32')
	baseline = model.forward(x)

	sid = sm.start_session(model, num_slices=2, encrypt=True)
	out = sm.infer(sid, x)
	sm.end_session(sid)

	assert np.allclose(out, baseline)
