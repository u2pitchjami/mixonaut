"""
2020-08-20 module de traitemment de la transposition.
"""

import random
import sqlite3
from mixonaut.db.analyse.transposition_queries import (
    insert_transpositions,
    get_bpm_context_by_id,
    fetch_tracks_with_bpm_and_key,
)
from mixonaut.utils.config import CAMELOT_ORDER, SEMITONE_SHIFT_VALUES
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.utils.utils_div import format_nb, format_percent


def is_related_tempo(a: float, b: float) -> bool:
    ratios = [0.5, 1.0, 2.0]

    for ratio in ratios:
        if abs(a - (b * ratio)) < 3:
            return True

    return False


def shift_camelot(key: str, shift: int, logger: LoggerProtocol | None = None) -> str:
    """
    Shifts the given key in the Camelot ordering by the specified amount.
    Args:
        key (str): The key to shift.
        shift (int): The number of positions to shift the key.
        logger (LoggerProtocol | None, optional): The logger to use for logging. Defaults to None.

    Returns:
        str: The shifted key.

    Raises:
        ValueError: If the given key is not found in the Camelot ordering.
    """
    logger = ensure_logger(logger, __name__)
    try:
        index = CAMELOT_ORDER.index(key)
        return CAMELOT_ORDER[(index + shift) % 24]
    except ValueError:
        logger.warning("Clé Camelot inconnue : %s", key)
        raise


def shift_bpm(bpm: float, semitone_shift: int) -> float:
    """
    Shift the BPM of a track based on a semitone shift.

    Args:
        bpm (float): The initial BPM.
        semitone_shift (int): The number of semitones to shift.

    Returns:
        float: The shifted BPM.
    """
    ratio = 2 ** (semitone_shift / 12)
    return round(bpm * ratio, 2)


def shift_to_colname(prefix: str, shift: int) -> str:
    """
    Shifts a Camelot key or BPM by a given number of semitones.

    This function shifts the input data according to the shift value. It returns a new string
    representing the shifted values, with the prefix and suffix updated accordingly.

    Parameters:
    prefix (str): The prefix of the output column name.
    shift (int): The number of semitones to shift by.

    Returns:
    str: The name of the column after shifting.
    """
    if shift == 0:
        return f"{prefix}_0"
    sign = "plus" if shift > 0 else "minus"
    return f"{prefix}_{sign}_{abs(shift)}"


def generate_transpositions(
    nb_limit: int | None = None,
    track_id: int | None = None,
    logger: LoggerProtocol | None = None,
) -> tuple[dict[str, int] | None, str, str | None]:
    logger = ensure_logger(logger, __name__)

    logger.debug("Arguments reçus : nb_limit=%s, track_id=%s", nb_limit, track_id)

    rows = fetch_tracks_with_bpm_and_key(logger=logger)

    def build_and_insert(row: sqlite3.Row) -> bool:
        tid = row["id"]
        key = row["initial_key"]

        bpm = choose_reference_bpm(
            bpm_main=row["madmom_bpm"],
            bpm_alt_1=row["bpm_alt_1"],
            bpm_alt_2=row["bpm_alt_2"],
            bpm_confidence=row["bpm_main_confidence"],
            fallback_bpm=row["essentia_bpm"],
        )

        if key in (None, "", "no_key"):
            logger.warning("⛔ Transpo skip track %s: key inexploitable=%s", tid, key)
            return False

        if bpm is None or bpm <= 0:
            logger.warning("⛔ Transpo skip track %s: bpm inexploitable=%s", tid, bpm)
            return False

        keys: dict[str, str] = {}
        bpms: dict[str, float] = {}

        for shift in SEMITONE_SHIFT_VALUES:
            key_col = shift_to_colname("key", shift)
            bpm_col = shift_to_colname("bpm", shift)
            keys[key_col] = shift_camelot(key, shift, logger=logger)
            bpms[bpm_col] = shift_bpm(bpm, shift)

        logger.debug(f"Transpo track {tid}: key={key} -> {keys}, bpm={bpm} -> {bpms}")
        insert_transpositions(tid, keys, bpms, logger=logger)
        return True

    if track_id is not None:
        filtered = [row for row in rows if row["id"] == track_id]

        if not filtered:
            return (
                None,
                "KO_UNSUPPORTED",
                f"Track ID {track_id} introuvable ou key/bpm manquants",
            )

        try:
            ok = build_and_insert(filtered[0])
            if not ok:
                return None, "KO_UNSUPPORTED", f"Track ID {track_id} inexploitable"

            return None, "OK", None

        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception(
                "❌ Transposition: erreur technique pour track %s", track_id
            )
            return None, "KO_FILE", str(exc)

    random.shuffle(rows)

    total = nb_limit or len(rows)
    selected_rows = rows[:total]

    logger.info("🎯 %s morceaux à traiter (batch)", format_nb(total, logger=logger))

    processed = 0

    try:
        for count, row in enumerate(selected_rows, start=1):
            logger.info(
                "🔍 Traitement du morceau %s - [%s/%s] (%s)",
                row["id"],
                format_nb(count, logger=logger),
                format_nb(total, logger=logger),
                format_percent(count, total, logger=logger),
            )

            try:
                if build_and_insert(row):
                    processed += 1
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "⛔ Erreur transposition pour track %s: %s",
                    row["id"],
                    exc,
                )

        logger.info("🏁 Terminé. %s transpositions réalisées", processed)
        return {"processed": processed}, "Mode Batch", None

    except Exception as exc:
        logger.exception("❌ [transpo] Erreur batch transposition")
        raise RuntimeError("Erreur batch transposition") from exc


def get_reference_bpm_by_id(
    track_id: int,
    logger: LoggerProtocol | None = None,
) -> float | None:
    bpm_context = get_bpm_context_by_id(
        track_id,
        logger=logger,
    )

    if bpm_context is None:
        return None

    return choose_reference_bpm(
        bpm_main=bpm_context.get("bpm_main"),
        bpm_alt_1=bpm_context.get("bpm_alt_1"),
        bpm_alt_2=bpm_context.get("bpm_alt_2"),
        bpm_confidence=bpm_context.get("bpm_main_confidence"),
        fallback_bpm=bpm_context.get("essentia_bpm"),
    )


def choose_reference_bpm(
    bpm_main: float | None,
    bpm_alt_1: float | None,
    bpm_alt_2: float | None,
    bpm_confidence: float | None,
    fallback_bpm: float | None,
) -> float | None:
    if bpm_main is None:
        return fallback_bpm

    if bpm_confidence is None:
        return bpm_main

    if bpm_confidence >= 0.25:
        return bpm_main

    alternatives = [bpm for bpm in (bpm_alt_1, bpm_alt_2) if bpm is not None]

    related_count = 0

    for bpm in alternatives:
        if is_related_tempo(bpm_main, bpm):
            related_count += 1

    if related_count >= 1:
        return bpm_main

    return fallback_bpm
