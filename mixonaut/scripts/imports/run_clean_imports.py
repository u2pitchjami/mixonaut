"""2025-08-20 - scripts de suppresssions des éléments du dossiers downloads + qbit."""

import argparse

from mixonaut.db.imports.import_queries import get_hashes_ready_for_deletion
from mixonaut.process_imports.post_imports.process_delete import (
    delete_torrents_and_files_by_hashes,
)
from mixonaut.process_imports.qbit.process_qbit import (
    import_completed_torrents,
    update_ratios_from_qbit,
)
from mixonaut.utils.config import QBIT_HOST, QBIT_PASS, QBIT_USER
from mixonaut.utils.logger import get_logger
from mixonaut.utils.safe_runner import safe_main

logger = get_logger("test_qbittorrent_supp")


@safe_main
def cleanup_completed_torrents(
    qbit_host: str,
    qbit_user: str,
    qbit_pass: str,
    min_ratio: int | float = 2.0,
    min_age_days: int = 30,
    grace_days_soft: int = 14,
    dry_run: bool = False,
) -> None:
    """Cleanup completed torrents and update QBit ratios.
    Args:
        qbit_host (str): QBit host URL.
        qbit_user (str): QBit username.
        qbit_pass (str): QBit password.
        min_ratio (float, optional): Minimum ratio to consider a torrent complete. Defaults to 2.0.
        min_age_days (int, optional): Minimum age of the torrent in days. Defaults to 30.
        grace_days_soft (int, optional): Soft grace period in days for torrents to
         be considered complete. Defaults to 14.
        dry_run (bool, optional): Whether to perform a dry run without actually deleting anything. Defaults to False.
        logger (Optional[Logger]): Logger instance. Defaults to None.

    Returns:
    """
    logger.info("🔄 Sync qBit → DB (torrents complétés) + ratios")
    import_completed_torrents(
        qbit_host=qbit_host, qbit_user=qbit_user, qbit_pass=qbit_pass, logger=logger
    )
    update_ratios_from_qbit(logger=logger)

    logger.info(
        "🔍 Sélection des hashes supprimables (ratio≥%.2f, age≥%dj, soft≥%dj)",
        min_ratio,
        min_age_days,
        grace_days_soft,
    )
    hashes = get_hashes_ready_for_deletion(
        min_ratio=min_ratio,
        min_age_days=min_age_days,
        grace_days_soft=grace_days_soft,
        logger=logger,
    )
    logger.info("🧹 Hashes à supprimer: %s", hashes)

    summary = delete_torrents_and_files_by_hashes(
        hashes,
        qbit_host=qbit_host,
        qbit_user=qbit_user,
        qbit_pass=qbit_pass,
        dry_run=dry_run,
        logger=logger,
    )
    logger.info("✅ Cleanup terminé. Résumé: %s", summary)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--qbit_host", default=QBIT_HOST)
    ap.add_argument("--qbit_user", default=QBIT_USER)
    ap.add_argument("--qbit_pass", default=QBIT_PASS)
    ap.add_argument("--min_ratio", type=float, default=2.0)
    ap.add_argument("--min_age_days", type=int, default=30)
    ap.add_argument("--grace_days_soft", type=int, default=14)
    ap.add_argument("--dry_run", action="store_true")
    args = ap.parse_args()
    cleanup_completed_torrents(
        qbit_host=args.qbit_host,
        qbit_user=args.qbit_user,
        qbit_pass=args.qbit_pass,
        min_ratio=args.min_ratio,
        min_age_days=args.min_age_days,
        grace_days_soft=args.grace_days_soft,
        dry_run=args.dry_run,
    )
