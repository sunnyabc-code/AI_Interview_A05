#!/usr/bin/env python
"""
Temporary SenseVoice verification script.

Goal:
- Input: one local audio file path (wav recommended)
- Output: recognized text

Example:
  python scripts/verify_sensevoice_asr.py --audio D:/data/test.wav
  python scripts/verify_sensevoice_asr.py --audio D:/data/test.wav --device cuda:0
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any


def _extract_text(data: Any) -> str:
    """Best-effort text extraction for different FunASR/SenseVoice output shapes."""
    if data is None:
        return ""

    if isinstance(data, str):
        return data.strip()

    if isinstance(data, dict):
        # Common keys from ASR outputs.
        for key in ("text", "asr_text", "sentence", "result"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        # Nested containers.
        for key in ("data", "output", "results", "value"):
            value = data.get(key)
            text = _extract_text(value)
            if text:
                return text

        # Fallback: scan all values.
        for value in data.values():
            text = _extract_text(value)
            if text:
                return text

        return ""

    if isinstance(data, (list, tuple)):
        parts = []
        for item in data:
            text = _extract_text(item)
            if text:
                parts.append(text)
        # Join unique consecutive parts to avoid noisy duplicates.
        merged = []
        for p in parts:
            if not merged or merged[-1] != p:
                merged.append(p)
        return " ".join(merged).strip()

    return ""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify SenseVoice ASR with one audio file")
    parser.add_argument("--audio", required=True, help="Path to input audio file (wav recommended)")
    parser.add_argument("--model", default="iic/SenseVoiceSmall", help="Model id/path")
    parser.add_argument("--device", default="cpu", help="Device, e.g. cpu or cuda:0")
    parser.add_argument("--language", default="zh", help="Language, e.g. zh/en")
    parser.add_argument(
        "--disable-itn",
        action="store_true",
        help="Disable text normalization (ITN). Default is enabled.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    audio_path = os.path.abspath(args.audio)
    if not os.path.exists(audio_path):
        print(f"[ERROR] audio file not found: {audio_path}")
        return 2

    try:
        from funasr import AutoModel
    except Exception as exc:  # noqa: BLE001
        print("[ERROR] failed to import funasr.AutoModel")
        print(f"detail: {exc}")
        print("hint: install dependencies from SenseVoice README first")
        return 3

    try:
        model = AutoModel(
            model=args.model,
            device=args.device,
            trust_remote_code=True,
            disable_update=True,
        )
    except Exception as exc:  # noqa: BLE001
        print("[ERROR] failed to load SenseVoice model")
        print(f"detail: {exc}")
        return 4

    try:
        # Parameters are intentionally minimal for compatibility.
        result = model.generate(
            input=audio_path,
            language=args.language,
            use_itn=not args.disable_itn,
        )
    except TypeError:
        # Some versions expect fewer args.
        result = model.generate(input=audio_path)
    except Exception as exc:  # noqa: BLE001
        print("[ERROR] SenseVoice inference failed")
        print(f"detail: {exc}")
        return 5

    text = _extract_text(result)
    if not text:
        print("[WARN] no text extracted from model output")
        print("raw output:")
        print(result)
        return 6

    print("[OK] transcript:")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
