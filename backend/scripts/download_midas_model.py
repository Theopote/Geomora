#!/usr/bin/env python3
"""Backward-compatible MiDaS downloader — prefer download_depth_models.py."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from download_depth_models import download_model  # noqa: E402


def main() -> int:
    return download_model("midas")


if __name__ == "__main__":
    sys.exit(main())
