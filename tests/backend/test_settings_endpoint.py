from fastapi.testclient import TestClient

from geomora_rectify.server import app


def test_settings_capabilities_never_return_secret_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret-value")
    monkeypatch.setenv("GEMINI_API_KEY", "another-secret")
    response = TestClient(app).get("/settings/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["cloud_providers"]["openai"]["configured"] is True
    assert payload["cloud_providers"]["gemini"]["configured"] is True
    assert payload["security"]["api_keys_returned"] is False
    assert "super-secret-value" not in response.text
    assert "another-secret" not in response.text


def test_session_credentials_are_accepted_but_never_returned():
    client = TestClient(app)
    response = client.post("/settings/credentials", json={
        "provider": "openai_compatible",
        "api_key": "session-secret",
        "base_url": "http://127.0.0.1:1234/v1",
    })
    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert response.json()["persisted"] is False
    capabilities = client.get("/settings/capabilities")
    assert capabilities.json()["cloud_providers"]["openai_compatible"]["configured"] is True
    assert "session-secret" not in capabilities.text


def test_credential_endpoint_rejects_unsafe_base_url():
    response = TestClient(app).post("/settings/credentials", json={
        "provider": "openai_compatible", "base_url": "file:///tmp/model"
    })
    assert response.status_code == 400


def test_connection_test_verifies_real_multimodal_contract(monkeypatch):
    client = TestClient(app)
    client.post("/settings/credentials", json={"provider": "openai", "api_key": "test-secret"})
    captured = {}

    def fake_request(image_path, **kwargs):
        captured.update(kwargs)
        assert image_path.exists()
        return object()

    monkeypatch.setattr("geomora_rectify.server.request_architectural_evidence", fake_request)
    response = client.post("/settings/test-connection", json={
        "provider": "openai", "model": "test-vision-model", "base_url": "https://example.test/v1"
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["vision_input"] is True
    assert payload["structured_output"] is True
    assert payload["model"] == "test-vision-model"
    assert captured["base_url"] == "https://example.test/v1"
    assert captured["timeout"] == 20.0
    assert captured["attempts"] == 1


def test_local_connection_requires_explicit_model_name():
    client = TestClient(app)
    client.post("/settings/credentials", json={
        "provider": "openai_compatible", "base_url": "http://127.0.0.1:1234/v1"
    })
    response = client.post("/settings/test-connection", json={
        "provider": "openai_compatible", "model": "auto"
    })
    assert response.json()["code"] == "model_required"
