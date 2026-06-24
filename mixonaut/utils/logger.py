"""2025-08-20 - logger du projet."""

from __future__ import annotations

import functools
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, ParamSpec, Protocol, TypeVar, cast

from mixonaut.utils.config import LOG_FILE_PATH, LOG_ROTATION_DAYS
from mixonaut.utils.log_rotation import rotate_logs


# ---------- Protocole (contrat) ----------
class LoggerProtocol(Protocol):
    """
    This is a protocol that defines the interface for a logger. It specifies the methods that must be implemented by any
    class that wants to be treated as a logger.

    The `debug`, `info`, `warning`, `error` and `exception` methods are used to log messages of different levels.

    The `get_child` method allows you to create child loggers, which can have their own set of handlers.
    """

    def debug(self, msg: str, *args: object, **kwargs: Any) -> None:
        """
        Logs a debug message with the given parameters.
        """
        ...

    def info(self, msg: str, *args: object, **kwargs: Any) -> None:
        """
        Logs a info message with the given parameters.
        """
        ...

    def warning(self, msg: str, *args: object, **kwargs: Any) -> None:
        """
        Logs a warning message with the given parameters.
        """
        ...

    def error(self, msg: str, *args: object, **kwargs: Any) -> None:
        """
        Logs a error message with the given parameters.
        """
        ...

    def exception(self, msg: str, *args: object, **kwargs: Any) -> None:
        """
        Logs a exception message with the given parameters.
        """
        ...

    def get_child(self, suffix: str) -> LoggerProtocol:
        """
        Get child logger.
        """
        ...


# ---------- Classe concrète (instanciable) ----------


@dataclass(frozen=True)
class MixonautLogger:
    """
    A logger class for Mixonaut projects.

    This logger is designed to provide a structured and organized way of logging messages at different levels.
    It uses the Python `logging` module to handle log messages, and provides methods for debugging,
    informing, warning, erroring, and exception handling. It also allows for easy rotation of logs
    after a specified number of days.

    Attributes:
        _base: The base logger instance.

    Methods:
        debug(msg: str, *args: object, **kwargs: Any) -> None: Logs a message at the debug level.
        info(msg: str, *args: object, **kwargs: Any) -> None: Logs a message at the information level.
        warning(msg: str, *args: object, **kwargs: Any) -> None: Logs a message at the warning level.
        error(msg: str, *args: object, **kwargs: Any) -> None: Logs a message at the error level.
        exception(msg: str, *args: object, **kwargs: Any) -> None: Logs a message at the exception level.
        get_child(suffix: str) -> LoggerProtocol: Gets a child logger instance with the specified suffix.
    """

    _base: logging.Logger

    # expose la même API que le Protocol
    def debug(self, msg: str, *args: object, **kwargs: Any) -> None:
        """
        Logs a message at the DEBUG level.

        :param msg: The message to log.
        :param args: Variable number of arguments to pass to the logger's debug method.
        :param kwargs: Keyword arguments to pass to the logger's debug method.
        """
        self._base.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: object, **kwargs: Any) -> None:
        """
        Logs a message at the INFO level.

        :param msg: The message to log.
        :param args: Variable number of arguments to pass to the logger's info method.
        :param kwargs: Keyword arguments to pass to the logger's info method.
        """
        self._base.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: object, **kwargs: Any) -> None:
        """
        Writes a warning message to the log.

        Args:
            msg (str): The warning message.
            *args: Variable number of non-keyword arguments. These are passed to the underlying logging function.
            **kwargs: Keyword arguments. These are passed to the underlying logging function.

        Returns:
            None
        """
        self._base.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: object, **kwargs: Any) -> None:
        """
        Raise an error when logging at this level. This is typically used to log critical information that the
        application cannot recover from.

        :param msg: The message to be logged.
        :param args: Variable number of arguments to be used in the log message.
        :param kwargs: Keyword arguments to be used in the log message.
        """
        self._base.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args: object, **kwargs: Any) -> None:
        """
        Override the exception method to include a formatted timestamp and message.

        This ensures that all log messages, including exceptions, are properly formatted with a timestamp. This is
        particularly useful for debugging purposes.
        """
        self._base.exception(msg, *args, **kwargs)

    def get_child(self, suffix: str) -> LoggerProtocol:
        """
        Creates a child logger with the specified suffix.

        Args:
        - suffix (str): The suffix to append to the original logger name.

        Returns:
        A new MixonautLogger instance that is a child of this logger.
        """
        return MixonautLogger(self._base.getChild(suffix))


def _ensure_handlers(
    base: logging.Logger, global_log_file: str, script_log_file: str
) -> None:
    if getattr(base, "_mixonaut_configured", False):
        return

    normal_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(name)s] %(message)s"
    )

    debug_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
    )

    # Console → debug détaillé
    stream = logging.StreamHandler()
    stream.setFormatter(debug_formatter)
    stream.setLevel(logging.DEBUG)
    base.addHandler(stream)

    # Log global → format compact
    fh_global = logging.FileHandler(
        global_log_file,
        encoding="utf-8",
    )
    fh_global.setFormatter(normal_formatter)
    fh_global.setLevel(logging.INFO)
    base.addHandler(fh_global)

    # Log script → debug détaillé
    fh_script = logging.FileHandler(
        script_log_file,
        encoding="utf-8",
    )
    fh_script.setFormatter(debug_formatter)
    fh_script.setLevel(logging.DEBUG)
    base.addHandler(fh_script)

    setattr(base, "_mixonaut_configured", True)


def get_logger(script_name: str) -> LoggerProtocol:
    """
    Constructeur de logeur.

    Cela créé les fichiers de logs si ils n'existent pas, met à jour le niveau d'accès des logs, configure les outils de
    rotation et réinitialise les gestionnaires de flux logiques.

    :param script_name: Nom du script.
    :return: Instanciation de logeur.
    """
    os.makedirs(LOG_FILE_PATH, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    global_log_file = os.path.join(LOG_FILE_PATH, f"{date_str}_Mixonaut.log")
    script_log_file = os.path.join(LOG_FILE_PATH, f"{date_str}_{script_name}.log")

    try:
        rotate_logs(LOG_FILE_PATH, LOG_ROTATION_DAYS, logf=script_log_file)
    except Exception as exc:  # noqa: BLE001
        base_fallback = logging.getLogger(script_name)
        base_fallback.setLevel(logging.DEBUG)
        _ensure_handlers(base_fallback, global_log_file, script_log_file)
        MixonautLogger(base_fallback).warning(f"Rotation des logs échouée: {exc}")

    base = logging.getLogger(script_name)
    base.setLevel(logging.DEBUG)
    _ensure_handlers(base, global_log_file, script_log_file)
    return MixonautLogger(base)  # ← classe concrète, pas le Protocol


# ---------- Utilities ----------
def ensure_logger(logger: LoggerProtocol | None, module: str) -> LoggerProtocol:
    """
    Ensure that a logger is available for the given module.

    If no logger is provided, return a new MixonautLogger instance.
    Otherwise, create a child logger with the given module name.

    Args:
        logger (LoggerProtocol | None): The logger to use, or None to create a new one.
        module (str): The name of the module for which to ensure a logger.

    Returns:
        LoggerProtocol: The ensured logger instance.
    """
    if logger is None:
        return get_logger(module)
    return logger


# ---------- Décorateur type-safe ----------
P = ParamSpec("P")
R = TypeVar("R")


def with_child_logger(func: Callable[P, R]) -> Callable[P, R]:
    """
    Définit un décorateur qui renvoie le résultat du décoré avec un filtreur de logger.

    :param func: La fonction à décorer
    :return: La fonction décorée avec un filtreur de logger
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        current = cast(Optional[LoggerProtocol], kwargs.get("logger"))
        kwargs["logger"] = ensure_logger(current, func.__module__)
        return func(*args, **kwargs)

    return wrapper
