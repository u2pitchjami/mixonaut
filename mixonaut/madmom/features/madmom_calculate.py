"""
2025-08-20.

modules de calcul du beat intensity .
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def compute_rhythm_stability(
    beat_interval_std: float | None,
) -> float | None:
    if beat_interval_std is None or beat_interval_std < 0:
        return None

    return round(1.0 / (1.0 + beat_interval_std), 4)


def compute_density(
    count: int | None,
    duration: float | None,
) -> float | None:
    if count is None or duration is None or duration <= 0:
        return None

    return round(count / duration, 4)


def compute_rhythm_intensity(
    beat_activation_mean: float | None,
    beat_activation_max: float | None,
    onsets_per_second: float | None,
    beats_per_second: float | None,
) -> float | None:
    values = [
        beat_activation_mean * 100 if beat_activation_mean is not None else None,
        beat_activation_max * 40 if beat_activation_max is not None else None,
        onsets_per_second * 10 if onsets_per_second is not None else None,
        beats_per_second * 20 if beats_per_second is not None else None,
    ]

    clean_values = [value for value in values if value is not None]

    if not clean_values:
        return None

    return round(sum(clean_values), 2)


def get_duration_with_ffprobe(audio_path: Path) -> float | None:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(audio_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        duration = data.get("format", {}).get("duration")

        if duration is None:
            return None

        return float(duration)

    except (subprocess.CalledProcessError, ValueError, json.JSONDecodeError):
        return None
