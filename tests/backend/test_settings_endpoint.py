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
