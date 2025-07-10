import argparse
from logic_imports.process_delete import delete_torrents_and_files
from logic_imports.process_qbit import import_completed_torrents, update_ratios_from_qbit
from utils.config import QBIT_HOST, QBIT_USER, QBIT_PASS
from db.import_queries import get_torrents_ready_for_deletion
from utils.logger import get_logger, with_child_logger
from datetime import datetime, timedelta

logger = get_logger("test_qbittorrent_supp")

@with_child_logger
def cleanup_completed_torrents(
    qbit_host: str = QBIT_HOST,
    qbit_user: str = QBIT_USER,
    qbit_pass: str = QBIT_PASS,
    min_ratio: float = 2.0,
    min_age_days: int = 30,
    dry_run: bool = True,
    logger=None
):
    logger.info("\u2728 Vérification des torrents complétés dans qBittorrent")
    import_completed_torrents(qbit_host=qbit_host, qbit_user=qbit_user, qbit_pass=qbit_pass, logger=logger)
    logger.info("\u2728 Mise à jour des ratios des torrents")
    update_ratios_from_qbit(logger=logger)
    logger.info("\u2728 Lancement du nettoyage des torrents complétés")
    torrents = get_torrents_ready_for_deletion(min_ratio=2.0, min_age_days=10, logger=logger)
    logger.info(f"🔍 Torrents prêts à être supprimés : {torrents}")
    delete_torrents_and_files(torrent_names=torrents, dry_run=True, qbit_host=qbit_host, qbit_user=qbit_user, qbit_pass=qbit_pass, logger=logger)
    logger.info("\u2728 Nettoyage terminé")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qbit_host", type=str, default=QBIT_HOST, help="Hôte qBittorrent")
    parser.add_argument("--qbit_user", type=str, default=QBIT_USER, help="Utilisateur qBittorrent")
    parser.add_argument("--qbit_pass", type=str, default=QBIT_PASS, help="Mot de passe qBittorrent")
    parser.add_argument("--min_ratio", type=float, default=2.0, help="Ratio minimum")
    parser.add_argument("--min_age_days", type=int, default=30, help="Ancienneté minimum en jours")
    parser.add_argument("--dry_run", action="store_true", help="Exécution en mode test (sans suppression réelle)")
    args = parser.parse_args()
    cleanup_completed_torrents(
        qbit_host=args.qbit_host,
        qbit_user=args.qbit_user,
        qbit_pass=args.qbit_pass,
        min_ratio=args.min_ratio,
        min_age_days=args.min_age_days,
        dry_run=args.dry_run,
        logger=logger
    )
