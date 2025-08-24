"""
20250820.

requêtes pour générer les embedding genres
"""

import sqlite3
from typing import TypedDict

from sklearn.decomposition import PCA

from mixonaut.db.access import select_all
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


class GenreEmbedding2D(TypedDict):
    id: int
    genre_emb_1: float
    genre_emb_2: float


# Configuration
GENRE_COLUMNS = [
    # Dortmund (10 genres)
    "genre_dortmund_alternative",
    "genre_dortmund_blues",
    "genre_dortmund_electronic",
    "genre_dortmund_folkcountry",
    "genre_dortmund_funksoulrnb",
    "genre_dortmund_jazz",
    "genre_dortmund_pop",
    "genre_dortmund_raphiphop",
    "genre_dortmund_rock",
    # Electronic (5 genres)
    "genre_electronic_ambient",
    "genre_electronic_dnb",
    "genre_electronic_house",
    "genre_electronic_techno",
    "genre_electronic_trance",
]


@with_child_logger
def compute_genre_embeddings(
    n_components: int = 2, logger: "LoggerProtocol | None" = None
) -> list[GenreEmbedding2D]:
    """
    Applique une PCA (2D) sur les vecteurs genre et retourne une liste
    de dicts: {"id": int, "genre_emb_1": float, "genre_emb_2": float}.
    """
    logger = ensure_logger(logger, __name__)
    if n_components != 2:
        logger.warning("n_components != 2 : la sortie attendue est 2D; forçage à 2.")
        n_components = 2

    try:
        cols = ", ".join(["id"] + GENRE_COLUMNS)
        query = f"SELECT {cols} FROM audio_features"
        rows: list[sqlite3.Row] | None = select_all(query, logger=logger)

        ids: list[int] = []
        vectors: list[list[float]] = []
        if rows:
            for row in rows:
                track_id = int(row[0])
                vec = row[1:]
                if None not in vec:
                    ids.append(track_id)
                    # conversion stricte en float
                    vectors.append([float(x) for x in vec])
                else:
                    logger.warning("Track %s ignoré : vecteur incomplet", track_id)

            if not vectors:
                logger.warning("Aucun vecteur genre valide trouvé.")
                return []

            pca = PCA(n_components=n_components)
            reduced = pca.fit_transform(vectors)

            results: list[GenreEmbedding2D] = []
            for i, track_id in enumerate(ids):
                results.append(
                    {
                        "id": track_id,
                        "genre_emb_1": round(float(reduced[i][0]), 4),
                        "genre_emb_2": round(float(reduced[i][1]), 4),
                    }
                )

            logger.info("%s embeddings genre (2D) générés.", len(results))
            return results
        return []
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Erreur PCA genre embedding : %s", exc)
        return []
