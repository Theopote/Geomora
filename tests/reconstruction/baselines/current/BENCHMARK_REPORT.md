# RC-G0 Frozen Baseline Report

- Source commit: `629e2a85e8cbfa7ce51fe64b2b6d4679b04b1154`
- Detector method: `facade_row_v1`
- Minimal set: 5 photos (3 holdout)
- GT validation: 5/5 pass, 0 errors, 0 warnings
- Freeze provenance: see `freeze_manifest.json`

## Gate result

RC-G0 **failed**. Mean RQS was 46.36 and mean coverage was 0.90, but mean
storey accuracy was 0.4667 against the 0.50 prototype threshold.

RC-G1 **failed**. It has only 3 holdout photos against the required 5 and
also misses detection, topology, geometry, RQS, and SketchUp thresholds. This
baseline does not support an Alpha or product-readiness claim.

| Photo | RQS | Window precision | Window recall | Storey accuracy | Bay accuracy | Geometry MAE |
|---|---:|---:|---:|---:|---:|---:|
| photo_01 | 58.8 | 0.2000 | 0.5000 | 0.5000 | 0.3750 | 0.1956 |
| photo_11 | 46.9 | 0.4167 | 0.8333 | 0.5000 | 0.7500 | 0.2185 |
| photo_16 | 43.7 | 0.5000 | 0.4000 | 0.3333 | 0.3750 | 0.1335 |
| photo_18 | 36.8 | 0.0000 | 0.0000 | 0.5000 | 0.3750 | not evaluated |
| photo_19 | 45.6 | 0.4000 | 0.3333 | 0.5000 | 0.5556 | 0.1865 |

## CI evidence

GitHub Actions run `32653925641` for verified predecessor `541450c` completed successfully.
Required Python, Ruby pure, static contract, reconstruction contract, and
package-smoke jobs passed. The non-blocking `ruby-full-suite-debt` job remains
failed and must continue to be tracked as debt. The local freeze/provenance
commit itself has not yet been verified by a remote CI run.

## Ablation status

The A-E ablation is **not recorded**. Its runner correctly requires a frozen
VLM evidence cache for every photo, and no valid five-photo cache is currently
present. Synthetic evidence or live cloud calls were not substituted. No claim
about VLM, Understanding, Metric Anchor, or Solver contribution should be made
until that cache is frozen and the paired run is completed.

## Decision

Do not change gate thresholds and do not claim RC-G0 acceptance. The next
benchmark action is to obtain and freeze reviewed VLM evidence for all five
photos, then run the existing A-E and paired CV-only/CV+VLM ablation unchanged.
Only that report should choose the next algorithm-development target.
