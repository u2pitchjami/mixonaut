"""
2025-08-19 module principal du script analyse_batch.

module utilisé par :
    - analyse_batch.py
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mixonaut.db.analyse.status_queries import update_table_status
from mixonaut.essentia.analyse.essentia_analyse import (
    analyse_track,
    analyse_track_wo_essentia,
)
from mixonaut.essentia.reuse.reuse_gate import try_reuse_essentia
from mixonaut.process_analyse.hash.chromaprint_integ import fingerprint_track
from mixonaut.process_analyse.retro_beets.sync_beets_from_essentia import (
    sync_fields_by_track_id,
)
from mixonaut.process_analyse.transposition.transposition import generate_transpositions
from mixonaut.utils.ensure_to import ensure_to_str
from mixonaut.utils.logger import LoggerProtocol, ensure_logger

# --- Codes & helpers ---------------------------------------------------------

OK = "OK"
KO_FILE = "KO_FILE"
KO_AUDIO = "KO_AUDIO"
KO = "KO"
SKIPPED = "SKIPPED"

StepFn = Callable[[], tuple[str, str]]


@dataclass
class StepResult:
    """
    A data class representing the result of a step in the analysis process.

    Attributes:
        code (str): The status code of the step.
        message (str, optional): Additional information about the step's outcome. Defaults to "".
    """

    code: str
    message: str = ""


def run_step(
    table: str, track_id: int, fn: StepFn, logger: LoggerProtocol | None = None
) -> StepResult:
    """
    Exécute une étape, met à jour le statut DB, gère les erreurs de manière homogène.
    """
    logger = ensure_logger(logger, __name__)
    try:
        code, msg = fn()
        update_table_status(table, track_id, code, msg or None, logger=logger)
        return StepResult(code=code, message=msg or "")
    except Exception as exc:  # pylint: disable=broad-except
        if logger:
            logger.exception("Step '%s' failed for track_id=%s", table, track_id)
        update_table_status(table, track_id, KO, str(exc), logger=logger)
        return StepResult(code=KO, message=str(exc))


def skip_step(
    table: str, track_id: int, reason: str, logger: LoggerProtocol | None = None
) -> StepResult:
    """
    Enregistre un statut SKIPPED dans la DB sans exécuter la tâche.
    """
    logger = ensure_logger(logger, __name__)
    update_table_status(table, track_id, SKIPPED, reason, logger=logger)
    return StepResult(code=SKIPPED, message=reason)


def analyse_hub(
    track: tuple[int, str, str, str, str],
    steps: list[str] | None = None,
    force: bool = False,
    max_length: int | None = None,
    timeout: int = 60,
    logger: LoggerProtocol | None = None,
) -> dict[str, tuple[str, str]]:
    """
    Hub modulaire d'analyse audio.

    Args:
        track: tuple (track_id, path, artist, title, album, ...)
        steps: ex: ['fingerprint', 'essentia', 'transposition']
        force: forcer l'analyse même si un JSON réutilisable existe
        timeout: délai max pour les sous-tâches externes
    Returns:
        dict[str, tuple[str, str]]
    """
    logger = ensure_logger(logger, __name__)
    if steps is None:
        steps = ["fingerprint", "essentia", "transposition"]

    results: dict[str, tuple[str, str]] = {}
    track_id = int(track[0])
    path = ensure_to_str(track[1])

    # 1) FINGERPRINT
    if "fingerprint" in steps:

        def _fingerprint() -> tuple[str, str]:
            code, msg = fingerprint_track(
                track_id=track_id,
                file_path=path,
                max_length=max_length,
                timeout=timeout,
                logger=logger,
            )
            return code, msg or ""

        fp_res = run_step("audio_hash", track_id, _fingerprint, logger)
        results["fingerprint"] = (fp_res.code, fp_res.message)
    else:
        fp_res = skip_step("audio_hash", track_id, "step not requested", logger)
        results["fingerprint"] = (SKIPPED, "step not requested")

    # 2) ESSENTIA (reuse + analyse)
    if "essentia" in steps:
        # Dépendance douce : si fingerprint KO et pas force, on skip Essentia
        if results["fingerprint"][0] in (KO, KO_FILE, KO_AUDIO, SKIPPED) and not force:
            fp_res = skip_step(
                "audio_features", track_id, "blocked by fingerprint", logger
            )
            results["essentia"] = (SKIPPED, "blocked by fingerprint")
            results["sync"] = (SKIPPED, "blocked by fingerprint")
        else:

            def _essentia() -> tuple[str, str]:
                reused = False
                track_features: dict[str, Any] | None = None
                error_code: str | None = None
                error_message: str | None = None
                json_path: Path | None = None
                if not force:
                    try:
                        json_path = try_reuse_essentia(track_id=track_id, logger=logger)
                    except Exception:  # pylint: disable=broad-except
                        if logger:
                            logger.exception(
                                "Reuse Essentia failed, fallback to full analysis"
                            )
                        json_path = None

                if json_path:
                    track_features, error_code, error_message = (
                        analyse_track_wo_essentia(
                            json_path=json_path,
                            track_id=track_id,
                            force=True,
                            logger=logger,
                        )
                    )
                    reused = track_features is not None

                if track_features is None:
                    # passe aussi timeout vers analyse_track si elle le supporte
                    track_features, error_code, error_message = analyse_track(
                        track, force=force, logger=logger
                    )

                if track_features is None:
                    # Echec global de l'étape Essentia
                    return (error_code or KO, error_message or "")

                # Sync beets, quelles que soient la source (reuse/analyse)
                sync_fields_by_track_id(
                    track_id=track_id, track_features=track_features, logger=logger
                )
                return (OK, "Reused existing JSON" if reused else "")

            ess_res = run_step("audio_features", track_id, _essentia, logger)
            results["essentia"] = (ess_res.code, ess_res.message)
            # Cohérence du statut 'sync'
            if ess_res.code == OK:
                results["sync"] = (OK, "From reused JSON" if ess_res.message else "")
            elif ess_res.code == SKIPPED:
                results["sync"] = (SKIPPED, "essentia skipped")
            else:
                results["sync"] = (SKIPPED, "essentia failed")
    else:
        fp_res = skip_step("audio_features", track_id, "step not requested", logger)
        results["essentia"] = (SKIPPED, "step not requested")
        results["sync"] = (SKIPPED, "step not requested")

    # 3) TRANSPOSITION
    if "transposition" in steps:
        # dépend d’Essentia sauf si logic interne supporte le fallback
        if results["essentia"][0] in (KO, KO_FILE, KO_AUDIO, SKIPPED) and not force:
            results["transposition"] = (SKIPPED, "blocked by essentia")
            fp_res = skip_step(
                "track_transpositions", track_id, "blocked by essentia", logger
            )
        else:

            def _transpo() -> tuple[str, str]:
                _data, code, msg = generate_transpositions(
                    track_id=track_id, logger=logger
                )
                return code, msg or ""

            tr_res = run_step("track_transpositions", track_id, _transpo, logger)
            results["transposition"] = (tr_res.code, tr_res.message)
    else:
        fp_res = skip_step(
            "track_transpositions", track_id, "step not requested", logger
        )
        results["transposition"] = (SKIPPED, "step not requested")

    return results
