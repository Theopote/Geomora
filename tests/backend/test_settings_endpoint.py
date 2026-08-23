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
