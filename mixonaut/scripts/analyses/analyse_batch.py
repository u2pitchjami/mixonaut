"""2025-08-20 - hub analyses : hash + essentia + transpo."""

from __future__ import annotations

import argparse

from mixonaut.db.analyse.essentia_queries import fetch_tracks
from mixonaut.db.analyse.status_queries import sync_pending_tables
from mixonaut.process_analyse.analyse_hub import analyse_hub
from mixonaut.utils.config import ALLOWED_STEPS, FPCALC_MAXLEN
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main
from mixonaut.utils.utils_div import format_nb  # , format_percent

logger = get_logger("Analyse_Batch")


def _parse_steps(s: str | None) -> list[str] | None:
    if not s:
        return None
    steps = [v.strip().lower() for v in s.split(",") if v.strip()]
    if steps == ["all"]:
        return None  # None => défaut dans main() = toutes les étapes
    unknown = [x for x in steps if x not in ALLOWED_STEPS]
    if unknown:
        raise argparse.ArgumentTypeError(
            f"Étapes inconnues: {unknown}. Autorisées: {sorted(ALLOWED_STEPS)}"
        )
    return steps


def _parse_list(s: str | None) -> list[str] | None:
    if not s:
        return None
    return [v.strip() for v in s.split(",") if v.strip()]


@safe_main
def main(
    force: bool = False,
    steps: list[str] | None = None,
    count: int | None = None,
    status_list: list[str] | None = None,
    missing_features: bool = False,
    mf_logic: str | None = "OR",
    is_edm: bool = False,
    missing_field: str | None = None,
    path_contains: str | None = None,
    track_id: int | None = None,
    max_length: int | None = None,
    timeout: int = 60,
) -> None:
    """
    Analyse batch of tracks.

    This function synchronizes pending tables, fetches tracks based on the provided
    filters and parameters, and then performs an analysis on each track using the
    `analyse_hub` function. The results are logged to the console.

    Parameters
    ----------
    force : bool, optional (default: False)
        Whether to force re-analysis of all tracks.
    steps : list[str], optional
        List of steps to perform on each track. Can be one of 'all' or a comma-separated
        list of allowed steps.
    count : int, optional
        Number of tracks to analyze. If not specified, all tracks are analyzed.
    status_list : list[str], optional
        List of statuses to filter tracks by.
    missing_features : bool, optional (default: False)
        Whether to include tracks with missing features in the analysis.
    mf_logic : str, optional (default: "OR")
        Logic operator to use when combining filters for missing features.
    is_edm : bool, optional (default: False)
        Whether to only analyze EDM tracks.
    missing_field : str, optional
        Field name to filter by if present in tracks.
    path_contains : str, optional
        Path to filter by if present in tracks.
    track_id : int, optional
        ID of a specific track to analyze.
    max_length : int, optional
        Maximum length for the analysis process.
    timeout : int (default: 60)
        Timeout for the analysis process.

    Notes
    -----
    The `sync_pending_tables` function is called before analyzing tracks. This ensures
    that all pending tables are up-to-date before performing the analysis.

    Raises
    ------
    ValueError
        If an unknown step is specified.
    """
    sync_pending_tables(logger=logger)

    logger.info("🔍 Lancement analyse batch avec steps=%s", steps or ["all"])

    tracks = fetch_tracks(
        missing_features=missing_features,
        mf_logic=mf_logic,
        status_list=status_list,
        is_edm=is_edm,
        missing_field=missing_field,
        path_contains=path_contains,
        track_id=track_id,
        logger=logger,
    )

    if not tracks:
        logger.info("Aucune piste à traiter.")
        return

    if not count:
        count = len(tracks)

    for idx, track in enumerate(tracks[:count], start=1):
        track_id = track[0]
        logger.info(
            "▶️  [%s/%s] Analyse track_id=%s",
            format_nb(idx, logger=logger),
            format_nb(count, logger=logger),
            track_id,
        )

        try:
            result = analyse_hub(
                track,
                steps=steps,
                force=force,
                max_length=max_length,
                timeout=timeout,
                logger=logger,
            )

            logger.info("✅ Résultats : %s", result)
        except Exception as e:
            logger.exception("❌ Erreur inattendue track_id=%s : %s", track_id, str(e))

    logger.info("🏁 Analyse terminée.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forcer l'analyse (ignore le reuse si applicable).",
    )
    parser.add_argument(
        "--steps",
        type=_parse_steps,
        default=None,
        help="Étapes à exécuter (ex: fingerprint,essentia,transposition). "
        "Utilise 'all' ou omets l'option pour tout lancer.",
    )
    parser.add_argument(
        "--status-list",
        dest="status_list",
        type=_parse_list,
        help="Filtre SQL: statuts à inclure (ex: PENDING,KO_FILE).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Nombre d'éléments à traiter (défaut: tous).",
    )
    parser.add_argument(
        "--missing-features",
        action="store_true",
        help="Limiter aux pistes sans features.",
    )
    parser.add_argument(
        "--mf_logic", type=str, default="OR", help="AND ou OR pour missing-features."
    )
    parser.add_argument(
        "--is-edm",
        action="store_true",
        help="Filtre genre EDM (si supporté par la requête).",
    )
    parser.add_argument(
        "--missing-field", type=str, help="Filtrer par champ manquant (ex: bpm,key...)."
    )
    parser.add_argument(
        "--path-contains", type=str, help="Filtrer par sous-chaîne dans le chemin."
    )
    parser.add_argument(
        "--track-id",
        type=int,
        default=None,
        help="Analyser un track_id précis (court-circuite la requête batch).",
    )
    parser.add_argument(
        "--fpcalc-length",
        type=int,
        default=FPCALC_MAXLEN,
        help="SPECIFIQUE FPCALC Limiter l'analyse à N secondes",
    )
    parser.add_argument(
        "--fpcalc-timeout",
        type=int,
        default=60,
        help="SPECIFIQUE FPCALC Timeout fpcalc (s)",
    )

    args = parser.parse_args()

    main(
        force=args.force,
        steps=args.steps,
        count=args.count,
        status_list=args.status_list,
        missing_features=args.missing_features,
        mf_logic=args.mf_logic,
        is_edm=args.is_edm,
        missing_field=args.missing_field,
        path_contains=args.path_contains,
        track_id=args.track_id,
        max_length=args.fpcalc_length,
        timeout=args.fpcalc_timeout,
    )
