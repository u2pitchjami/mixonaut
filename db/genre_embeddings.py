from sklearn.decomposition import PCA
from utils.logger import get_logger
from db.access import select_all

# Configuration
GENRE_COLUMNS = [
    # Dortmund (10 genres)
    "genre_dortmund_alternative", "genre_dortmund_blues", "genre_dortmund_electronic",
    "genre_dortmund_folkcountry", "genre_dortmund_funksoulrnb", "genre_dortmund_jazz",
    "genre_dortmund_pop", "genre_dortmund_raphiphop", "genre_dortmund_rock",
    # Electronic (5 genres)
    "genre_electronic_ambient", "genre_electronic_dnb", "genre_electronic_house",
    "genre_electronic_techno", "genre_electronic_trance"
]

def compute_genre_embeddings(n_components: int = 2, logname: str = "Genre_Embeddings"):
    logger = get_logger(logname)
    try:
        cols = ", ".join(["id"] + GENRE_COLUMNS)
        query = f"SELECT {cols} FROM audio_features"
        rows = select_all(query, logname=logname)

        ids = []
        vectors = []

        for row in rows:
            track_id = row[0]
            vec = row[1:]
            if None not in vec:
                ids.append(track_id)
                vectors.append(list(vec))
            else:
                logger.warning(f"Track {track_id} ignoré : vecteur incomplet")

        if not vectors:
            logger.warning("Aucun vecteur genre valide trouvé.")
            return []

        pca = PCA(n_components=n_components)
        reduced = pca.fit_transform(vectors)

        results = []
        for i, track_id in enumerate(ids):
            entry = {"id": track_id}
            for d in range(n_components):
                entry[f"genre_emb_{d+1}"] = round(float(reduced[i][d]), 4)
            results.append(entry)

        logger.info(f"{len(results)} embeddings genre générés.")
        return results

    except Exception as e:
        logger.error(f"Erreur PCA genre embedding : {e}")
        return []
