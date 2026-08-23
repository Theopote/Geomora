"""Generate cached VLM architectural evidence for one facade image."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_reconstruct.vlm_evidence import (  # noqa: E402
    read_evidence_cache,
    request_architectural_evidence,
    write_evidence_cache,
)
from geomora_reconstruct.observations.vlm_adapter import vlm_evidence_to_observations  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--photo-id", required=True)
    parser.add_argument("--provider", choices=("openai", "gemini"), default="openai")
    parser.add_argument("--model")
    parser.add_argument("--api-key")
    parser.add_argument("--base-url")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--observation-graph", type=Path)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    model = args.model or ("gemini-2.5-flash" if args.provider == "gemini" else "gpt-4o-mini")
    if args.cache.exists() and not args.refresh:
        evidence = read_evidence_cache(args.cache)
        if evidence.photo_id != args.photo_id:
            raise ValueError("cache photo_id does not match --photo-id")
        print(f"Using cached evidence: {args.cache}")
    else:
        key = args.api_key or os.environ.get("OPENAI_API_KEY" if args.provider == "openai" else "GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError(f"missing API key for {args.provider}")
        evidence = request_architectural_evidence(args.image, photo_id=args.photo_id, provider=args.provider, model=model, api_key=key, base_url=args.base_url)
        write_evidence_cache(args.cache, evidence)
        print(f"Evidence saved: {args.cache}")

    if args.observation_graph:
        import json

        graph = vlm_evidence_to_observations(evidence)
        args.observation_graph.parent.mkdir(parents=True, exist_ok=True)
        args.observation_graph.write_text(json.dumps(graph.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Observation graph saved: {args.observation_graph}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
