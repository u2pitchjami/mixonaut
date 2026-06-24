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
from mixonaut.madmom.analyse.madmom_analyse import (
    analyse_track_madmom,
    analyse_track_wo_madmom,
)
from mixonaut.madmom.reuse.reuse_gate import try_reuse_madmom
from mixonaut.process_analyse.hash.chromaprint_integ import fingerprint_track
from mixonaut.process_analyse.retro_beets.sync_beets_from_essentia import (
    sync_fields_by_track_id,
)
from mixonaut.process_analyse.transposition.transposition import generate_transpositions
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.process_analyse.prep_analyse import prep_track, clean_temp_files

# --- Codes & helpers ---------------------------------------------------------

OK = "OK"
KO_FILE = "KO_FILE"
KO_AUDIO = "KO_AUDIO"
KO = "KO"
SKIPPED = "SKIPPED"
TOO_LONG = "TOO_LONG"

StepFn = Callable[[], tuple[str, str]]

MAX_DURATION = 900


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
    # update_table_status(table, track_id, SKIPPED, reason, logger=logger)
    return StepResult(code=SKIPPED, message=reason)


def analyse_hub(
    track: tuple[int, str, str, str, str, str, str, str, str, float | None],
    steps: list[str] | None = None,
    force: bool = False,
    max_length: int | None = None,
    timeout: int = 60,
    logger: LoggerProtocol | None = None,
) -> dict[str, tuple[str, str]]:
    """
    Hub modulaire d'analyse audio.
    """
    logger = ensure_logger(logger, __name__)

    if steps is None:
        steps = ["fingerprint", "essentia", "madmom", "transposition"]

    results: dict[str, tuple[str, str]] = {}
    track_id = int(track[0])
    duration = track[9]

    temp_audio: Path | None = None
    temp_json: Path | None = None
    temp_json_madmom: Path | None = None

    requires_audio_prep = any(
        step in ("fingerprint", "essentia", "madmom") for step in steps
    )

    if requires_audio_prep:
        logger.info("Préparation audio requise: track_id=%s", track_id)
        (
            track_id,
            _original_path,
            _safe_name,
            temp_audio,
            temp_json,
            temp_json_madmom,
        ) = prep_track(track, logger=logger)

    # 1) FINGERPRINT
    if "fingerprint" in steps:
        logger.info("Lancement Fingerprint: track_id=%s", track_id)

        def _fingerprint() -> tuple[str, str]:
            if temp_audio is None:
                return KO_FILE, "temp_audio missing"

            code, msg = fingerprint_track(
                track_id=track_id,
                file_path=str(temp_audio),
                max_length=max_length,
                timeout=timeout,
                logger=logger,
            )
            return code, msg or ""

        fp_res = run_step("audio_hash", track_id, _fingerprint, logger)
        results["fingerprint"] = (fp_res.code, fp_res.message)
    else:
        skip_step("audio_hash", track_id, "step not requested", logger)
        results["fingerprint"] = (SKIPPED, "step not requested")

    logger.info(
        "Fin Fingerprint: track_id=%s fingerprint=%s",
        track_id,
        results["fingerprint"],
    )

    # 2) ESSENTIA
    if "essentia" in steps:
        if results["fingerprint"][0] in (KO, KO_FILE, KO_AUDIO) and not force:
            skip_step("audio_features", track_id, "blocked by fingerprint", logger)
            results["essentia"] = (SKIPPED, "blocked by fingerprint")
            results["sync"] = (SKIPPED, "blocked by fingerprint")
        elif duration and duration > MAX_DURATION:
            logger.warning(
                "Skipping essentia for long track: %s (%ss)",
                track_id,
                duration,
            )
            ess_res = run_step(
                "audio_features",
                track_id,
                lambda: (TOO_LONG, "track too long"),
                logger,
            )
            results["essentia"] = (ess_res.code, ess_res.message)
            results["sync"] = (SKIPPED, "essentia too long")
        else:
            logger.info("Lancement Essentia: track_id=%s", track_id)

            def _essentia() -> tuple[str, str]:
                if temp_audio is None or temp_json is None:
                    return KO_FILE, "temp_audio or temp_json missing"

                reused = False
                track_features: dict[str, Any] | None = None
                error_code: str | None = None
                error_message: str | None = None
                json_path_ess: Path | None = None

                if not force:
                    try:
                        json_path_ess = try_reuse_essentia(
                            track_id=track_id,
                            logger=logger,
                        )
                    except Exception:
                        logger.exception(
                            "Reuse Essentia failed, fallback to full analysis"
                        )

                if json_path_ess:
                    track_features, error_code, error_message = (
                        analyse_track_wo_essentia(
                            json_path=json_path_ess,
                            track_id=track_id,
                            force=True,
                            logger=logger,
                        )
                    )
                    reused = track_features is not None

                if track_features is None:
                    track_features, error_code, error_message = analyse_track(
                        track_id=track_id,
                        temp_audio=temp_audio,
                        temp_json=temp_json,
                        force=force,
                        logger=logger,
                    )

                if track_features is None:
                    return error_code or KO, error_message or ""

                sync_fields_by_track_id(
                    track_id=track_id,
                    track_features=track_features,
                    logger=logger,
                )

                return OK, "Reused existing JSON" if reused else ""

            ess_res = run_step("audio_features", track_id, _essentia, logger)
            results["essentia"] = (ess_res.code, ess_res.message)

            if ess_res.code == OK:
                results["sync"] = (
                    OK,
                    "From reused JSON" if ess_res.message else "",
                )
            elif ess_res.code == SKIPPED:
                results["sync"] = (SKIPPED, "essentia skipped")
            else:
                results["sync"] = (SKIPPED, "essentia failed")
    else:
        skip_step("audio_features", track_id, "step not requested", logger)
        results["essentia"] = (SKIPPED, "step not requested")
        results["sync"] = (SKIPPED, "step not requested")

    logger.info("Fin Essentia: track_id=%s essentia=%s", track_id, results["essentia"])

    # 3) MADMOM
    if "madmom" in steps:
        if results["essentia"][0] in (KO, KO_FILE, KO_AUDIO) and not force:
            skip_step("madmom_features", track_id, "blocked by essentia", logger)
            results["madmom"] = (SKIPPED, "blocked by essentia")
        elif duration and duration > MAX_DURATION:
            logger.warning(
                "Skipping madmom for long track: %s (%ss)",
                track_id,
                duration,
            )
            madmom_res = run_step(
                "madmom_features",
                track_id,
                lambda: (TOO_LONG, "track too long"),
                logger,
            )
            results["madmom"] = (madmom_res.code, madmom_res.message)
        else:
            logger.info("Lancement Madmom: track_id=%s", track_id)

            def _madmom() -> tuple[str, str]:
                if temp_audio is None or temp_json_madmom is None:
                    return KO_FILE, "temp_audio or temp_json_madmom missing"

                reused = False
                madmom_features: dict[str, Any] | None = None
                error_code: str | None = None
                error_message: str | None = None
                json_path_mm: Path | None = None

                if not force:
                    try:
                        json_path_mm = try_reuse_madmom(
                            track_id=track_id,
                            logger=logger,
                        )
                    except Exception:
                        logger.exception(
                            "Reuse madmom failed, fallback to full analysis"
                        )

                if json_path_mm:
                    logger.info(
                        "Reuse madmom trouvé pour track_id=%s : %s",
                        track_id,
                        json_path_mm,
                    )
                    madmom_features, error_code, error_message = (
                        analyse_track_wo_madmom(
                            json_path=json_path_mm,
                            track_id=track_id,
                            file_path=temp_audio,
                            duration=duration,
                            force=True,
                            logger=logger,
                        )
                    )
                    reused = madmom_features is not None

                if madmom_features is None:
                    logger.info(
                        "Reuse madmom non trouvé ou invalide pour track_id=%s, lancement analyse complète",
                        track_id,
                    )
                    madmom_features, error_code, error_message = analyse_track_madmom(
                        temp_audio=temp_audio,
                        temp_json=temp_json_madmom,
                        track_id=track_id,
                        duration=duration,
                        force=force,
                        logger=logger,
                    )

                if madmom_features is None:
                    return error_code or KO, error_message or ""

                return OK, "Reused existing JSON" if reused else ""

            madmom_res = run_step("madmom_features", track_id, _madmom, logger)
            results["madmom"] = (madmom_res.code, madmom_res.message)
    else:
        skip_step("madmom_features", track_id, "step not requested", logger)
        results["madmom"] = (SKIPPED, "step not requested")

    logger.info("Fin Madmom: track_id=%s madmom=%s", track_id, results["madmom"])

    # 4) TRANSPOSITION
    if "transposition" in steps:
        if results["madmom"][0] in (KO, KO_FILE, KO_AUDIO) and not force:
            skip_step("track_transpositions", track_id, "blocked by madmom", logger)
            results["transposition"] = (SKIPPED, "blocked by madmom")
        elif duration and duration > MAX_DURATION:
            logger.warning(
                "Skipping transposition for long track: %s (%ss)",
                track_id,
                duration,
            )
            tr_res = run_step(
                "track_transpositions",
                track_id,
                lambda: (TOO_LONG, "track too long"),
                logger,
            )
            results["transposition"] = (tr_res.code, tr_res.message)
        else:
            logger.info("Lancement Transposition: track_id=%s", track_id)

            def _transpo() -> tuple[str, str]:
                _data, code, msg = generate_transpositions(
                    track_id=track_id,
                    logger=logger,
                )
                return code, msg or ""

            tr_res = run_step("track_transpositions", track_id, _transpo, logger)
            results["transposition"] = (tr_res.code, tr_res.message)
    else:
        skip_step("track_transpositions", track_id, "step not requested", logger)
        results["transposition"] = (SKIPPED, "step not requested")

    logger.info(
        "Fin Transposition: track_id=%s transposition=%s",
        track_id,
        results["transposition"],
    )
    clean_temp_files(
        temp_audio,
        temp_json,
        temp_json_madmom,
        logger=logger,
    )

    return results
