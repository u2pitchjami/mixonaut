from __future__ import annotations
from typing import Optional, Callable, Tuple, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

from process_analyse.hash.chromaprint_integ import fingerprint_track
from process_analyse.retro_beets.sync_beets_from_essentia import sync_fields_by_track_id
from process_analyse.transposition.transposition import generate_transpositions
from db.analyse.status_queries import update_table_status
from essentia.analyse.essentia_analyse import analyse_track, analyse_track_wo_essentia
from essentia.reuse.reuse_gate import try_reuse_essentia
from utils.utils_div import ensure_to_path


# --- Codes & helpers ---------------------------------------------------------

OK = "OK"
KO_FILE = "KO_FILE"
KO_AUDIO = "KO_AUDIO"
KO = "KO"
SKIPPED = "SKIPPED"

StepFn = Callable[[], Tuple[str, str]]

@dataclass
class StepResult:
    code: str
    message: str = ""


def run_step(table: str, track_id: int, fn: StepFn, logger=None) -> StepResult:
    """Exécute une étape, met à jour le statut DB, gère les erreurs de manière homogène."""
    try:
        code, msg = fn()
        update_table_status(table, track_id, code, msg or None, logger=logger)
        return StepResult(code=code, message=msg or "")
    except Exception as exc:  # pylint: disable=broad-except
        if logger:
            logger.exception("Step '%s' failed for track_id=%s", table, track_id)
        update_table_status(table, track_id, KO, str(exc), logger=logger)
        return StepResult(code=KO, message=str(exc))


def analyse_hub(
    track: tuple,
    steps: Optional[List[str]] = None,
    force: bool = False,
    max_length: Optional[int] = None,
    timeout: int = 60,
    logger=None
) -> Dict[str, Tuple[str, str]]:
    """Hub modulaire d'analyse audio.

    Args:
        track: tuple (track_id, path, artist, title, album, ...)
        steps: ex: ['fingerprint', 'essentia', 'transposition']
        force: forcer l'analyse même si un JSON réutilisable existe
        timeout: délai max pour les sous-tâches externes
    Returns:
        dict[str, tuple[str, str]]
    """
    if steps is None:
        steps = ['fingerprint', 'essentia', 'transposition']

    results: Dict[str, Tuple[str, str]] = {}
    track_id = int(track[0])
    path = ensure_to_path(track[1])

    # 1) FINGERPRINT
    if 'fingerprint' in steps:
        def _fingerprint() -> Tuple[str, str]:
            code, msg = fingerprint_track(
                track_id=track_id,
                file_path=path,
                max_length=max_length,
                timeout=timeout,
                logger=logger
            )
            return code, msg or ""
        fp_res = run_step("audio_hash", track_id, _fingerprint, logger)
        results['fingerprint'] = (fp_res.code, fp_res.message)
        print(results['fingerprint'])
    else:
        results['fingerprint'] = (SKIPPED, 'step not requested')

    # 2) ESSENTIA (reuse + analyse)
    if 'essentia' in steps:
        # Dépendance douce : si fingerprint KO et pas force, on skip Essentia
        if results['fingerprint'][0] in (KO, KO_FILE, KO_AUDIO, SKIPPED) and not force:
            results['essentia'] = (SKIPPED, 'blocked by fingerprint')
            results['sync'] = (SKIPPED, 'blocked by fingerprint')
        else:
            def _essentia() -> Tuple[str, str]:
                reused = False
                track_features: Optional[Dict[str, Any]] = None
                error_code: Optional[str] = None
                error_message: Optional[str] = None

                json_path: Optional[Path] = None
                if not force:
                    try:
                        json_path = try_reuse_essentia(track_id=track_id, logger=logger)
                    except Exception:  # pylint: disable=broad-except
                        if logger:
                            logger.exception("Reuse Essentia failed, fallback to full analysis")
                        json_path = None

                if json_path:
                    track_features, error_code, error_message = analyse_track_wo_essentia(
                        json_path=json_path,
                        track_id=track_id,
                        force=True,
                        logger=logger
                    )
                    reused = track_features is not None

                if track_features is None:
                    # passe aussi timeout vers analyse_track si elle le supporte
                    track_features, error_code, error_message = analyse_track(
                        track,
                        force=force,
                        source="Mixonaut",
                        logger=logger
                    )

                if track_features is None:
                    # Echec global de l'étape Essentia
                    return (error_code or KO, error_message or "")

                # Sync beets, quelles que soient la source (reuse/analyse)
                sync_fields_by_track_id(track_id=track_id, track_features=track_features, logger=logger)
                return (OK, 'Reused existing JSON' if reused else "")
            ess_res = run_step("audio_features", track_id, _essentia, logger)
            results['essentia'] = (ess_res.code, ess_res.message)
            # Cohérence du statut 'sync'
            if ess_res.code == OK:
                results['sync'] = (OK, 'From reused JSON' if ess_res.message else "")
            elif ess_res.code == SKIPPED:
                results['sync'] = (SKIPPED, 'essentia skipped')
            else:
                results['sync'] = (SKIPPED, 'essentia failed')
    else:
        results['essentia'] = (SKIPPED, 'step not requested')
        results['sync'] = (SKIPPED, 'step not requested')

    # 3) TRANSPOSITION
    if 'transposition' in steps:
        # dépend d’Essentia sauf si logic interne supporte le fallback        
        if results['essentia'][0] in (KO, KO_FILE, KO_AUDIO, SKIPPED) and not force:            
            results['transposition'] = (SKIPPED, 'blocked by essentia')
        else:
            def _transpo() -> Tuple[str, str]:
                _data, code, msg = generate_transpositions(track_id=track_id, logger=logger)
                return code, msg or ""
            tr_res = run_step("track_transpositions", track_id, _transpo, logger)
            results['transposition'] = (tr_res.code, tr_res.message)
    else:
        results['transposition'] = (SKIPPED, 'step not requested')

    return results
