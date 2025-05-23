import json
from typing import List
from sklearn.decomposition import PCA
from utils.config import MOOD_KEYS
from db.access import execute_query
from utils.logger import get_logger

def compute_mood_embeddings(n_components: int = 2, logname: str = "Mix_Assist") -> List[dict]:
    """
    Applique une réduction PCA sur les vecteurs mood pour chaque track.
    Retourne une liste de dictionnaires avec id, mood_x, mood_y.
    """
    logger = get_logger(logname)
    try:
        mood_cols = ", ".join([f"mood_{m}_probability" for m in MOOD_KEYS])
        query = f"SELECT id, {mood_cols} FROM tracks"
        rows = execute_query(query, fetch=True)

        ids = []
        vectors = []

        for row in rows:
            try:
                vec = [float(row[f"mood_{m}_probability"]) for m in MOOD_KEYS]
                if all(v is not None for v in vec):
                    ids.append(row["id"])
                    vectors.append(vec)
            except Exception as e:
                logger.warning(f"Track {row.get('id', '?')} ignoré : {e}")

        if not vectors:
            logger.warning("Aucun vecteur mood valide trouvé.")
            return []

        pca = PCA(n_components=n_components)
        reduced = pca.fit_transform(vectors)

        results = []
        for i, track_id in enumerate(ids):
            entry = {"id": track_id}
            for d in range(n_components):
                entry[f"mood_emb_{d+1}"] = round(float(reduced[i][d]), 4)
            results.append(entry)

        return results

    except Exception as e:
        logger.error(f"Erreur PCA mood embedding : {e}")
        return []
