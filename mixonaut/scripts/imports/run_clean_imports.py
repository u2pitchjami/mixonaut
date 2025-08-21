import argparse
from process_imports.post_imports.process_delete import delete_torrents_and_files_by_hashes
from utils.safe_runner import safe_main
from process_imports.qbit.process_qbit import import_completed_torrents, update_ratios_from_qbit
from utils.config import QBIT_HOST, QBIT_USER, QBIT_PASS
from db.imports.import_queries import get_hashes_ready_for_deletion
from utils.logger import get_logger, with_child_logger

logger = get_logger("test_qbittorrent_supp")
@safe_main
@with_child_logger
def cleanup_completed_torrents(qbit_host, qbit_user, qbit_pass,
                               min_ratio=2.0, min_age_days=30, grace_days_soft=14,
                               dry_run=False, logger=None):
    logger.info("🔄 Sync qBit → DB (torrents complétés) + ratios")
    import_completed_torrents(qbit_host=qbit_host, qbit_user=qbit_user, qbit_pass=qbit_pass, logger=logger)
    update_ratios_from_qbit(logger=logger)

    logger.info("🔍 Sélection des hashes supprimables (ratio≥%.2f, age≥%dj, soft≥%dj)", min_ratio, min_age_days, grace_days_soft)
    hashes = get_hashes_ready_for_deletion(min_ratio=min_ratio, min_age_days=min_age_days,
                                           grace_days_soft=grace_days_soft, logger=logger)
    logger.info("🧹 Hashes à supprimer: %s", hashes)

    delete_torrents_and_files_by_hashes(hashes, qbit_host=qbit_host, qbit_user=qbit_user,
                                        qbit_pass=qbit_pass, dry_run=dry_run, logger=logger)
    logger.info("✅ Cleanup terminé.")

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
    cleanup_completed_torrents(qbit_host=args.qbit_host, qbit_user=args.qbit_user, qbit_pass=args.qbit_pass,
                               min_ratio=args.min_ratio, min_age_days=args.min_age_days,
                               grace_days_soft=args.grace_days_soft, dry_run=args.dry_run, logger=logger)