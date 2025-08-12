from utils.logger import get_logger
from logic.chromaprint_integ import _abspath, fingerprint_track
from db.fingerprint_queries import list_missing_or_bad
from utils.config import MUSIC_BASE_PATH, FPCALC_MAXLEN
from typing import Optional, Sequence, Tuple
from pathlib import Path
import argparse

def backfill_missing_from_db(host_music_root: Path,
                             limit: Optional[int] = None,
                             *,
                             max_length: Optional[int] = None,
                             timeout: int = 60,
                             prefer_json: bool = False,
                             logger=None) -> Tuple[int, int]:
    """
    Parcourt les items sans empreinte OK (vue via list_missing_or_bad) et tente le fingerprint.
    Retourne (nb_ok, nb_err).
    """
    rows: Sequence[Tuple[int, str]] = list_missing_or_bad(logger=logger)
    if limit is not None:
        rows = rows[:limit]

    ok = err = 0
    logger.info("🎧 Fingerprint backfill: %d fichiers à traiter", len(rows))
    for track_id, path in rows:
        abs_path = _abspath(host_music_root, path)
        success, _ = fingerprint_track(
            track_id=track_id,
            file_path=str(abs_path),
            max_length=max_length,
            timeout=timeout,
            prefer_json=prefer_json,
            logger=logger,
        )        
        if success:
            ok += 1
        else:
            err += 1
    logger.info("✅ Backfill terminé: ok=%d, err=%d", ok, err)
    return ok, err


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chromaprint integration")
    parser.add_argument("--host", type=str, default=str(MUSIC_BASE_PATH), help="host des fichiers")
    parser.add_argument("--limit", type=int, default=1, help="Limiter le nb de fichiers traités")
    parser.add_argument("--length", type=int, default=FPCALC_MAXLEN, help="Limiter l'analyse à N secondes")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout fpcalc (s)")
    parser.add_argument("--json", action="store_true", help="Tenter -json puis fallback")
    args = parser.parse_args()

    log = get_logger("chromaprint_integ")
    
    backfill_missing_from_db(host_music_root=Path(args.host), limit=args.limit, max_length=args.length, timeout=args.timeout, prefer_json=args.json, logger=log)

