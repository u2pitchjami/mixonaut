import argparse
from datetime import datetime
from db.sync_db import mark_missing_tracks, sync_paths, check_technical_differences
from utils.logger import get_logger

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Beets via MB (globale ou ciblée)")
    args = parser.parse_args()
    logname = "Sync_DB"
    logger = get_logger(logname)

    logger.info(f"📅 SYNC DB : {datetime.now().strftime('%d-%m-%Y')}")
    mark_missing_tracks(logname=logname)     
    sync_paths(logname=logname)
    check_technical_differences(logname=logname)       
    logger.info(f"🏁 SYNC DB : TERMINE !! \n\n")