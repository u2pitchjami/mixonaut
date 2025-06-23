from db.mood_embedding import compute_mood_embeddings
from db.essentia_queries import insert_or_update_audio_features
from utils.logger import get_logger
logname = __name__.split(".")[-1]

if __name__ == "__main__":
    logger = get_logger(logname)
    try:
        result = compute_mood_embeddings(logname=logname)
        for row in result:
            tid = row["id"]
            features = {
                "mood_emb_1": row["mood_emb_1"],
                "mood_emb_2": row["mood_emb_2"]
            }
            insert_or_update_audio_features(item_id=tid, features=features, force=True, logname=logname)
    except Exception as e:
        logger.exception("Erreur lors de la mise à jour des mood embeddings")
        raise