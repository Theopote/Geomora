"""List Gemini models available for the current API key."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_detect.vlm_prelabel import build_client, list_gemini_models  # noqa: E402


def main() -> None:
    import os

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY first.")

    models = list_gemini_models(api_key)
    if not models:
        print("No generateContent models returned for this key.")
        raise SystemExit(1)

    print("Available Gemini models:")
    for model in models:
        print(f"  - {model}")

    print()
    print("Suggested default:")
    for candidate in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"):
        if candidate in models:
            print(f"  {candidate}")
            break
    else:
        print(f"  {models[0]}")


if __name__ == "__main__":
    main()
