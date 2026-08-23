from __future__ import annotations

import os
from threading import RLock

_lock = RLock()
_credentials: dict[str, str] = {}
_base_urls: dict[str, str] = {}


def configure_provider(provider: str, *, api_key: str | None = None, base_url: str | None = None) -> None:
    name = provider.strip().lower()
    if name not in {"openai", "gemini", "openai_compatible"}:
        raise ValueError("unsupported VLM provider")
    with _lock:
        if api_key is not None:
            value = api_key.strip()
            if value:
                _credentials[name] = value
            else:
                _credentials.pop(name, None)
        if base_url is not None:
            value = base_url.strip().rstrip("/")
            if value and not value.startswith(("http://", "https://")):
                raise ValueError("base URL must start with http:// or https://")
            if value:
                _base_urls[name] = value
            else:
                _base_urls.pop(name, None)


def provider_api_key(provider: str) -> str | None:
    name = provider.strip().lower()
    with _lock:
        runtime = _credentials.get(name)
    if runtime:
        return runtime
    if name in {"openai", "openai_compatible"}:
        environment = os.getenv("OPENAI_API_KEY")
        if environment:
            return environment
        if name == "openai_compatible":
            with _lock:
                if _base_urls.get(name):
                    return "local-endpoint"
    if name == "gemini":
        return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return None


def provider_base_url(provider: str, configured: str | None = None) -> str | None:
    if configured and configured.strip():
        return configured.strip().rstrip("/")
    with _lock:
        return _base_urls.get(provider.strip().lower())


def credential_status(provider: str) -> dict[str, object]:
    name = provider.strip().lower()
    with _lock:
        in_session = bool(_credentials.get(name))
    with _lock:
        local_endpoint = name == "openai_compatible" and bool(_base_urls.get(name))
    source = "session" if in_session or local_endpoint else "environment"
    return {"configured": bool(provider_api_key(name)), "credential_source": source}
