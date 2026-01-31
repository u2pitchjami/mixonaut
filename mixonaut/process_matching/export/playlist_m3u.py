from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from mixonaut.process_matching.models.models import (
    EnrichedTrackMatch,  # adapte l'import
)
from mixonaut.utils.logger import LoggerProtocol, ensure_logger


def build_playlist_filename(
    *,
    track_id: int,
    target_bpm: float | None,
) -> str:
    """
    Build a human-readable playlist filename.

    Example:
      260131_128bpm_compatible_tracks_26815.m3u
      260131_refbpm_compatible_tracks_26815.m3u
    """
    date_str = datetime.now().strftime("%y%m%d")

    if target_bpm is not None:
        bpm_part = f"{int(round(target_bpm))}bpm"
    else:
        bpm_part = "refbpm"

    return f"{date_str}_{bpm_part}_compatible_tracks_{track_id}.m3u"


def generate_m3u_from_matches(
    matches: Iterable[EnrichedTrackMatch],
    playlist_path: Path,
    *,
    include_extinf: bool = True,
    sort_by_score: bool = True,
    logger: LoggerProtocol | None = None,
) -> Path:
    logger = ensure_logger(logger, __name__)
    logger.info("Generating M3U playlist: %s", playlist_path)

    tracks = list(matches)  # 🔒 éviter les itérateurs consommés
    logger.debug("Number of tracks to write: %d", len(tracks))

    try:
        logger.info("PLAYLIST STEP 1 | before mkdir")
        playlist_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("PLAYLIST STEP 2 | after mkdir")

        if sort_by_score:
            tracks.sort(key=lambda m: m.get("score", 0.0), reverse=True)

        written = 0
        logger.info("PLAYLIST STEP 3 | before open")
        with playlist_path.open("w", encoding="utf-8") as f:
            logger.info("PLAYLIST STEP 4 | file opened")
            f.write("#EXTM3U\n")
            logger.info("PLAYLIST STEP 5 | header written")
            for match in tracks:
                raw_path = match.get("path")

                if not raw_path:
                    logger.warning(
                        "Skipping track without path (id=%s)",
                        match.get("id"),
                    )
                    continue

                # normalisation path
                path_str = str(raw_path).strip()
                if not path_str or path_str == "Unknown":
                    logger.warning(
                        "Skipping track with invalid path (id=%s)",
                        match.get("id"),
                    )
                    continue

                artist = match.get("artist", "Unknown Artist")
                title = match.get("title", "Unknown Title")

                # 🔥 FIX ICI
                duration = match.get("features", {}).get("duration", -1)
                try:
                    duration_int = int(float(duration))
                except (TypeError, ValueError):
                    duration_int = -1

                if include_extinf:
                    f.write(f"#EXTINF:{duration_int},{artist} - {title}\n")

                f.write(f"{path_str}\n")
                written += 1

        logger.info(
            "Playlist generated: %s (%d tracks written)",
            playlist_path,
            written,
        )
        logger.info(
            "PLAYLIST FINAL CHECK | exists=%s | size=%d",
            playlist_path.exists(),
            playlist_path.stat().st_size if playlist_path.exists() else -1,
        )

        return playlist_path

    except Exception as exc:  # ⚠️ catch large pour debug
        logger.exception("Failed to generate M3U playlist")
        raise RuntimeError("Playlist generation failed") from exc
