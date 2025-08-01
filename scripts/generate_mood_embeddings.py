from db.mood_embedding import compute_mood_embeddings
from utils.safe_runner import safe_main
from db.essentia_queries import insert_or_update_audio_features
from utils.logger import get_logger

@safe_main
def main():
    logger = get_logger("Generate_Mood_Embeddings")
    result = compute_mood_embeddings(logger=logger)
    for row in result:
        tid = row["id"]
        features = {
            "mood_emb_1": row["mood_emb_1"],
            "mood_emb_2": row["mood_emb_2"]
        }
        insert_or_update_audio_features(item_id=tid, features=features, force=True, logger=logger)

if __name__ == "__main__":
    main()