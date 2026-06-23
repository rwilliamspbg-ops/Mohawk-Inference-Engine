"""Tests for GUI-facing controller service wiring endpoints."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from prototype import controller_service


@pytest.fixture(autouse=True)
def reset_controller_state():
    original = deepcopy(controller_service.STATE)
    yield
    controller_service.STATE.clear()
    controller_service.STATE.update(original)


@pytest.fixture
def client(monkeypatch):
    # Keep endpoint behavior deterministic in unit tests.
    monkeypatch.setattr(controller_service, "_check_worker_health", lambda host, port: "Connected")
    return TestClient(controller_service.app)


def test_models_load_and_download_flow(client):
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) >= 1

    download = client.post("/api/models/download", json={"model_id": "org/new-model"})
    assert download.status_code == 200
    assert download.json()["status"] == "ok"

    load = client.post("/api/models/load", json={"model": "org/new-model"})
    assert load.status_code == 200
    assert load.json()["model"] == "org/new-model"


def test_workers_add_and_connect(client):
    add = client.post("/api/workers/add", json={"host": "localhost", "port": 9000})
    assert add.status_code == 200
    assert add.json()["status"] == "ok"

    workers = client.get("/api/workers")
    assert workers.status_code == 200
    workers_data = workers.json()["workers"]
    assert any(w["host"] == "localhost" and w["port"] == 9000 for w in workers_data)

    connect = client.post("/api/workers/connect")
    assert connect.status_code == 200
    assert connect.json()["connected"] >= 1


def test_chat_queue_sessions_and_security_endpoints(client):
    queue = client.post("/api/queue", json={"priority": "high"})
    assert queue.status_code == 200
    assert queue.json()["job"]["priority"] == "high"

    chat = client.post(
        "/api/inference/chat",
        json={
            "message": "hello",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 256,
            "system_prompt": "test",
        },
    )
    assert chat.status_code == 200
    assert "response" in chat.json()

    sessions = client.get("/api/sessions")
    assert sessions.status_code == 200
    assert "sessions" in sessions.json()

    cancel = client.post("/api/sessions/sess_001/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "ok"

    jwt = client.post("/api/security/jwt/refresh")
    assert jwt.status_code == 200
    assert jwt.json()["status"] == "ok"

    pqc = client.post("/api/security/pqc/enable")
    assert pqc.status_code == 200
    assert pqc.json()["pqc_enabled"] is True
