import os
import logging
from datetime import datetime
from utils.log_rotation import rotate_logs
from utils.config import LOG_ROTATION_DAYS, LOG_FILE_PATH

def get_logger(name: str) -> logging.Logger:
    log_path = os.getenv("LOG_FILE_PATH", "logs")
    rotation_days = int(os.getenv("LOG_ROTATION_DAYS", "30"))

    os.makedirs(log_path, exist_ok=True)
    log_file = os.path.join(LOG_FILE_PATH, f"{datetime.now().strftime('%Y-%m')}_{name.split('.')[0]}.log")

    rotate_logs(log_path, rotation_days, logf=log_file)

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Console
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # Fichier
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
