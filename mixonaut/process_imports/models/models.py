from typing_extensions import NotRequired, TypedDict

# --- Types renvoyés par l'API qBit -------------------------------------------------


class QbtTorrent(TypedDict, total=False):
    hash: str
    name: str
    category: str
    tags: str
    progress: float  # 0.0..1.0
    state: str
    size: int
    completed: int
    completion_on: int
    save_path: str
    content_path: str
    ratio: float  # souvent présent, mais pas toujours -> total=False


class QbtFile(TypedDict, total=False):
    name: str
    size: int
    progress: float
    is_seed: bool
    path: str


class TorrentFullInfo(TypedDict):
    hash: str
    size: int
    files: list[QbtFile]
    name: str
    ratio: float
    # champs optionnels selon ce que renvoie l'API
    save_path: NotRequired[str]
    added_on: NotRequired[int]  # epoch sec
    completion_on: NotRequired[int]  # epoch sec


class FileToStage(TypedDict, total=False):
    id: int
    torrent_hash: str
    torrent_name: str
    relpath: str
    name: str
    size: int
    save_path: str | None
