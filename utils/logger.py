import os
import logging
import functools
from datetime import datetime
from utils.log_rotation import rotate_logs
from utils.config import LOG_ROTATION_DAYS, LOG_FILE_PATH

def get_logger(script_name: str) -> logging.Logger:
    os.makedirs(LOG_FILE_PATH, exist_ok=True)
    rotation_days = int(os.getenv("LOG_ROTATION_DAYS", "30"))
    
    global_log_file = os.path.join(LOG_FILE_PATH, f"{datetime.now().strftime('%Y-%m-%d')}_Mixonaut.log")
    script_log_file = os.path.join(LOG_FILE_PATH, f"{datetime.now().strftime('%Y-%m-%d')}_{script_name}.log")

    rotate_logs(LOG_FILE_PATH, rotation_days, logf=script_log_file)

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] %(message)s')

        # Console
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # Fichier global
        global_handler = logging.FileHandler(global_log_file, encoding='utf-8')
        global_handler.setFormatter(formatter)
        logger.addHandler(global_handler)

        # Fichier spécifique script
        script_handler = logging.FileHandler(script_log_file, encoding='utf-8')
        script_handler.setFormatter(formatter)
        logger.addHandler(script_handler)

    return logger


def with_child_logger(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = kwargs.get('logger', None)
        module_name = func.__module__

        if logger is None:
            logger = logging.getLogger(module_name)
            logger.warning(f"{module_name} : Logger non fourni, utilisation d'un logger par défaut.")
        else:
            logger = logger.getChild(module_name)

        kwargs['logger'] = logger
        return func(*args, **kwargs)

    return wrapper

# Exemple d'utilisation :
# from utils.logger import with_child_logger
#
# @with_child_logger
# def ma_fonction(arg1, arg2, logger=None):
#     logger.info("Coucou depuis ma_fonction")
