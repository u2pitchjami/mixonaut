from datetime import datetime
from db.access import execute_query
from utils.logger import get_logger

def update_tracks_meta(
    track_id: int,
    energy_level: float = None,
    beat_intensity: float = None,
    mood: str = None,
    mood_emb_1: float = None,
    mood_emb_2: float = None,
    essentia_genres: str = None,
    key: str = None,
    bpm: float = None,
    rg_gain: float = None,
    force: bool = True,
    logname: str = "mix_assist"
):
    logger = get_logger(logname)

    fields = {}
    if energy_level is not None:
        fields["energy_level"] = energy_level
    if beat_intensity is not None:
        fields["beat_intensity"] = beat_intensity
    if mood is not None:
        fields["mood"] = mood
    if mood_emb_1 is not None:
        fields["mood_emb_1"] = mood_emb_1
    if mood_emb_2 is not None:
        fields["mood_emb_2"] = mood_emb_2
    if essentia_genres is not None:
        fields["essentia_genres"] = essentia_genres
    if key is not None:
        fields["key"] = key
    if bpm is not None:
        fields["bpm"] = bpm
    if rg_gain is not None:
        fields["rg_gain"] = rg_gain
    
        
    fields["updated_at"] = datetime.now().isoformat(timespec="seconds")
    
    if not fields:
        logger.warning("Aucune donnée à mettre à jour dans tracks.")
        return
    
    allowed_fields = list(fields.keys())

    if force:
        assignments = ", ".join(f"{col} = ?" for col in allowed_fields)
    else:
        assignments = ", ".join(f"{col} = CASE WHEN {col} IS NULL THEN ? ELSE {col} END" for col in allowed_fields)

    query = f"""
        UPDATE tracks
        SET {assignments}
        WHERE id = ?
    """
    values = [fields[col] for col in allowed_fields] + [track_id]
    execute_query(query, tuple(values))

    
def ensure_columns_exist(table: str, columns: dict, logname: str = "Mixonaut"):
    """
    Vérifie que les colonnes existent dans la table, les crée si absentes.

    Args:
        table (str): nom de la table cible
        columns (dict): {colonne: type_sql}
    """
    logger = get_logger(logname)
    pragma_query = f"PRAGMA table_info({table});"
    result = execute_query(pragma_query, fetch=True)
    existing = {col[1] for col in result}

    for col, col_type in columns.items():
        if col not in existing:
            logger.info(f"Ajout de la colonne manquante : {col} ({col_type})")
            alter = f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"
            execute_query(alter)
