#!/usr/bin/env python3
"""CLI helper for rectification without running the HTTP server."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from geomora_rectify.pipeline import parse_corners, rectify_image


def main() -> None:
    parser = argparse.ArgumentParser(description="Rectify a perspective facade image")
    parser.add_argument("image", help="Input image path")
    parser.add_argument("-o", "--output", default="rectified.jpg", help="Output image path")
    parser.add_argument("--corners", help="JSON array of four [x,y] corner points")
    args = parser.parse_args()

    corners = parse_corners(args.corners) if args.corners else None
    result = rectify_image(args.image, output_path=args.output, corners=corners, return_base64=False)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
