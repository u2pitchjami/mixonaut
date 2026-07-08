"""2025-08-20 - hub analyses : hash + essentia + transpo."""

from __future__ import annotations

import argparse
from datetime import datetime
from uuid import uuid4
from mixonaut.db.analyse.essentia_queries import fetch_tracks
from mixonaut.db.analyse.status_queries import sync_pending_tables
from mixonaut.process_analyse.analyse_hub import analyse_hub
from mixonaut.utils.config import ALLOWED_STEPS, FPCALC_MAXLEN, EFFECTIVE_STATUS_LIST
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main
from mixonaut.utils.utils_div import format_nb
from mixonaut.db.analyse.claim_queries import (
    claim_tracks,
    refresh_track_claim,
    release_track_claim,
    count_active_claim_batches,
)

logger = get_logger("Analyse_Batch")


def build_batch_identity(
    run_source: str,
    worker_id: str | None = None,
    batch_id: str | None = None,
) -> tuple[str, str]:
    if worker_id is None:
        worker_id = f"mixonaut-{run_source}"

    if batch_id is None:
        batch_id = f"{worker_id}-{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:8]}"

    return worker_id, batch_id


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


def add_step(steps: list[str], step: str) -> None:
    if step not in steps:
        steps.append(step)


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
    run_source: str = "manual",
    worker_id: str | None = None,
    max_active_batches: int = 4,
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

    active_batches = count_active_claim_batches(logger=logger)

    if active_batches >= args.max_active_batches:
        logger.info(
            "⏸️  Trop de batchs actifs : %s/%s. Sortie sans traitement.",
            active_batches,
            args.max_active_batches,
        )
        return

    worker_id, batch_id = build_batch_identity(
        run_source=args.run_source,
        worker_id=args.worker_id,
    )

    run_source = args.run_source

    logger.info(
        "🔍 Lancement analyse batch avec steps=%s | worker_id=%s | batch_id=%s",
        steps or ["all"],
        worker_id,
        batch_id,
    )

    tracks = fetch_tracks(
        missing_features=missing_features,
        mf_logic=mf_logic if mf_logic is not None else "OR",
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

    candidate_tracks = tracks[:count]

    track_ids = [int(row["id"]) for row in candidate_tracks]

    claimed_track_ids = claim_tracks(
        track_ids=track_ids,
        worker_id=worker_id,
        batch_id=batch_id,
        run_source=run_source,
        ttl_hours=2,
        logger=logger,
    )

    claimed_track_ids_set = set(claimed_track_ids)

    tracks_to_process = [
        row for row in candidate_tracks if int(row["id"]) in claimed_track_ids_set
    ]

    if not tracks_to_process:
        logger.info(
            "Aucune piste claimée pour ce batch. "
            "Elles sont peut-être déjà réservées par une autre instance."
        )
        return

    count = len(tracks_to_process)

    for idx, track in enumerate(tracks_to_process, start=1):
        track_id = int(track[0])

        # Important : steps local à cette track.
        # On évite que les steps calculés pour une track contaminent les suivantes.
        track_steps = list(steps) if steps is not None else []

        if missing_features and not force:
            logger.info(
                "▶️  [%s/%s] Analyse track_id=%s (missing features)",
                format_nb(idx, logger=logger),
                format_nb(count, logger=logger),
                track_id,
            )

            essentia_status = track[5]
            madmom_status = track[6]
            transposition_status = track[7]
            hash_status = track[8]

            if essentia_status in EFFECTIVE_STATUS_LIST:
                add_step(track_steps, "essentia")

            if madmom_status in EFFECTIVE_STATUS_LIST:
                add_step(track_steps, "madmom")

            if hash_status in EFFECTIVE_STATUS_LIST:
                add_step(track_steps, "fingerprint")

            if transposition_status in EFFECTIVE_STATUS_LIST:
                add_step(track_steps, "transposition")

            if "essentia" in track_steps or "madmom" in track_steps:
                add_step(track_steps, "transposition")

        logger.info(
            "▶️  [%s/%s] Analyse track_id=%s | steps=%s",
            format_nb(idx, logger=logger),
            format_nb(count, logger=logger),
            track_id,
            track_steps or ["all"],
        )

        try:
            refresh_track_claim(
                track_id=track_id,
                batch_id=batch_id,
                ttl_hours=6,
                logger=logger,
            )

            result = analyse_hub(
                tuple(track),
                steps=track_steps if track_steps else steps,
                force=force,
                max_length=max_length,
                timeout=timeout,
                logger=logger,
            )

            logger.info("✅ Résultats track_id=%s : %s", track_id, result)

        except Exception as e:
            logger.exception(
                "❌ Erreur inattendue track_id=%s : %s. "
                "Claim conservé jusqu'à expiration.",
                track_id,
                str(e),
            )

        else:
            release_track_claim(
                track_id=track_id,
                batch_id=batch_id,
                logger=logger,
            )

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
    parser.add_argument(
        "--run-source",
        choices=["manual", "cronboss"],
        default="manual",
        help="Source du lancement : manual ou cronboss.",
    )
    parser.add_argument(
        "--worker-id",
        default=None,
        help="Identifiant lisible du worker. Si absent, généré depuis run-source.",
    )
    parser.add_argument(
        "--max-active-batches",
        type=int,
        default=4,
        help="Nombre maximum de batchs Mixonaut actifs en parallèle.",
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
        run_source=args.run_source,
        worker_id=args.worker_id,
        max_active_batches=args.max_active_batches,
    )
