"""
20250820.

requêtes pour générer les embedding mood
"""

import sqlite3
from typing import TypedDict

from sklearn.decomposition import PCA

from mixonaut.db.access import execute_query
from mixonaut.utils.config import MOOD_KEYS
from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger


class MoodEmbedding2D(TypedDict):
    id: int
    mood_emb_1: float
    mood_emb_2: float


@with_child_logger
def compute_mood_embeddings(
    n_components: int = 2, logger: LoggerProtocol | None = None
) -> list[MoodEmbedding2D]:
    """
    Applique une réduction PCA sur les vecteurs mood pour chaque track.

    Retourne une liste de dictionnaires avec id, mood_x, mood_y.
    """
    logger = ensure_logger(logger, __name__)
    if n_components != 2:
        logger.warning("n_components != 2 : la sortie attendue est 2D; forçage à 2.")
        n_components = 2
    try:
        mood_cols = ", ".join([f"mood_{m}_probability" for m in MOOD_KEYS])
        query = f"SELECT id, {mood_cols} FROM audio_features"
        rows: list[sqlite3.Row] | None = execute_query(query, fetch=True)

        ids: list[int] = []
        vectors: list[list[float]] = []

        if not rows:
            logger.warning("Aucune donnée retournée par la requête.")
            return []

        for row in rows:
            try:
                track_id = row[0]
                vec = [
                    float(row[i + 1]) for i in range(len(MOOD_KEYS))
                ]  # mood values start at index 1
                if all(v is not None for v in vec):
                    ids.append(track_id)
                    vectors.append(vec)
            except Exception as e:
                logger.warning(
                    f"Track {track_id if 'track_id' in locals() else '?'} ignoré : {e}"
                )

        if not vectors:
            logger.warning("Aucun vecteur mood valide trouvé.")
            return []

        pca = PCA(n_components=n_components)
        reduced = pca.fit_transform(vectors)

        results: list[MoodEmbedding2D] = []
        for i, track_id in enumerate(ids):
            results.append(
                {
                    "id": track_id,
                    "mood_emb_1": round(float(reduced[i][0]), 4),
                    "mood_emb_2": round(float(reduced[i][1]), 4),
                }
            )

        logger.info(f"{len(results)} embeddings mood générés.")
        return results

    except Exception as e:
        logger.error(f"Erreur PCA mood embedding : {e}")
        return []
