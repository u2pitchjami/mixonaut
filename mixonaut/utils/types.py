"""2025-08-20 - module de class pour les types."""

from __future__ import annotations

from typing import TypedDict


class ProcessResult(TypedDict):
    """
    Represents the result of a process.

    Attributes:
        stdout (str): The standard output of the process.
        stderr (str): The standard error of the process.
        returncode (int): The return code of the process.
    """

    stdout: str
    stderr: str
    returncode: int


class TranspoInfo(TypedDict):
    """
    A dictionary containing information about transportation data.

    Attributes:
        track_id (int): The ID of the transport track.
        keys (str): The keys used to access the transport data.
        bpms (float): The beats per minute of the transport data.
    """

    track_id: int
    keys: dict[str, str]
    bpms: dict[str, float]
