"""Create a reviewed, reproducible VLM evidence cache for a benchmark set."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_reconstruct.vlm_evidence import (  # noqa: E402
    PROMPT_VERSION,
    read_evidence_cache,
    request_architectural_evidence,
    write_evidence_cache,
)
from geomora_detect.vlm_prelabel import (  # noqa: E402
    GEMINI_MODEL_CANDIDATES,
    gemini_generate_url,
    gemini_headers,
    list_gemini_models,
    post_json_with_retries,
    sanitize_error_message,
)

DEFAULT_SET = REPO_ROOT / "tests/reconstruction/minimal_set.json"
DEFAULT_OUT = BACKEND_ROOT / "cache/vlm_architecture_frozen"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("openai", "gemini"), default="gemini")
    parser.add_argument("--model")
    parser.add_argument("--minimal-set", type=Path, default=DEFAULT_SET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preflight-only", action="store_true", help="Validate credentials/model access without uploading images")
    parser.add_argument(
        "--authorize-cloud-upload", action="store_true",
        help="Required acknowledgement that benchmark images may be uploaded to the selected provider",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model = args.model or ("gemini-2.5-flash" if args.provider == "gemini" else "gpt-4o-mini")
    minimal = _json(args.minimal_set)
    benchmark_manifest = _json(REPO_ROOT / minimal["manifest"])
    entries = {item["id"]: item for item in benchmark_manifest["images"]}
    selected = [item["id"] for item in minimal["photos"]]
    image_rows = []
    for photo_id in selected:
        entry = entries[photo_id]
        image_path = REPO_ROOT / benchmark_manifest["image_root"] / entry["file"]
        if not image_path.exists():
            raise FileNotFoundError(f"benchmark image missing: {image_path}")
        image_rows.append((photo_id, image_path))

    print(f"Provider: {args.provider}; model: {model}; prompt: {PROMPT_VERSION}")
    for photo_id, image_path in image_rows:
        print(f"  {photo_id}: {image_path.relative_to(REPO_ROOT)}")
    if args.dry_run:
        print("Dry run only; no images were uploaded.")
        return 0
    if not args.authorize_cloud_upload and not args.preflight_only:
        raise ValueError("refusing cloud upload without --authorize-cloud-upload")

    env_name = "GEMINI_API_KEY" if args.provider == "gemini" else "OPENAI_API_KEY"
    api_key = os.environ.get(env_name)
    if args.provider == "gemini" and not api_key:
        api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(f"missing {env_name}; set it in this terminal without placing it on the command line")
    if args.provider == "gemini":
        print("Checking Gemini model availability (20 second timeout)...", flush=True)
        try:
            available_models = list_gemini_models(api_key, timeout=20.0)
        except Exception as error:
            safe_error = sanitize_error_message(str(error), api_key)
            raise RuntimeError(
                "Gemini model preflight failed before any image upload. "
                f"Check network/proxy access to generativelanguage.googleapis.com. Detail: {safe_error}"
            ) from error
        if not available_models:
            raise ValueError("this API key exposes no Gemini model supporting generateContent")
        preferred = [model, *GEMINI_MODEL_CANDIDATES]
        compatible_models = []
        for candidate in preferred:
            if candidate in available_models and candidate not in compatible_models:
                compatible_models.append(candidate)
        if not compatible_models:
            visible = ", ".join(available_models[:12])
            raise ValueError(
                "none of Geomora's reviewed Gemini models is available for this key; "
                f"account reports: {visible}"
            )
        probe_payload = {
            "contents": [{"role": "user", "parts": [{"text": "Reply with the single word OK."}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 8},
        }
        resolved_model = None
        rejected_models = []
        for candidate in compatible_models:
            print(f"Probing Gemini generateContent model {candidate} (30 second timeout)...", flush=True)
            try:
                probe = post_json_with_retries(
                    gemini_generate_url(candidate), probe_payload,
                    headers=gemini_headers(api_key), timeout=30.0, attempts=1,
                )
                if not probe.get("candidates"):
                    raise RuntimeError("Gemini probe returned no candidates")
                resolved_model = candidate
                break
            except Exception as error:
                status_code = getattr(getattr(error, "response", None), "status_code", None)
                if status_code in {400, 404}:
                    rejected_models.append(f"{candidate} ({status_code})")
                    print(f"  rejected by generateContent: HTTP {status_code}", flush=True)
                    continue
                safe_error = sanitize_error_message(str(error), api_key)
                raise RuntimeError(
                    "Gemini generateContent POST failed before any image upload. "
                    "The network or proxy is not returning generation responses. "
                    f"Detail: {safe_error}"
                ) from error
        if resolved_model is None:
            raise RuntimeError(
                "Gemini lists reviewed models but generateContent rejected all of them: "
                + ", ".join(rejected_models)
            )
        if resolved_model != model:
            print(f"Requested model is unusable; selected verified model: {resolved_model}")
        model = resolved_model
        print(f"Gemini generateContent POST passed: {model}", flush=True)
    if args.preflight_only:
        print("Preflight only; no images were uploaded.")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    evidence_rows = []
    for photo_id, image_path in image_rows:
        cache_path = args.out / f"{photo_id}.json"
        if cache_path.exists() and not args.refresh:
            evidence = read_evidence_cache(cache_path)
            if evidence.photo_id != photo_id or evidence.provider != args.provider or evidence.model != model:
                raise ValueError(f"existing cache metadata mismatch: {cache_path}; use --refresh intentionally")
            action = "reused"
        else:
            print(f"[UPLOADING] {photo_id}...", flush=True)
            evidence = request_architectural_evidence(
                image_path, photo_id=photo_id, provider=args.provider,
                model=model, api_key=api_key,
            )
            write_evidence_cache(cache_path, evidence)
            # Parse the on-disk representation again before admitting it to the frozen set.
            read_evidence_cache(cache_path)
            action = "created"
        evidence_rows.append({
            "photo_id": photo_id,
            "image_sha256": _sha256(image_path),
            "evidence_sha256": _sha256(cache_path),
            "cache": cache_path.name,
        })
        print(f"[{action.upper()}] {photo_id}: {cache_path}")

    frozen = {
        "schema_version": "vlm-evidence-freeze-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_commit": _source_commit(),
        "provider": args.provider,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "minimal_set_sha256": _sha256(args.minimal_set),
        "photo_count": len(evidence_rows),
        "evidence": evidence_rows,
        "review_status": "pending_human_review",
    }
    freeze_path = args.out / "freeze_manifest.json"
    freeze_path.write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Freeze manifest saved: {freeze_path}")
    print("Next: review all five JSON files before changing review_status to reviewed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
