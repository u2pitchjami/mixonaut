import sqlite3
from pathlib import Path
from utils.config import BEETS_DB

def create_tables():
    with sqlite3.connect(BEETS_DB) as conn:
        cursor = conn.cursor()
        
        # Table des features analytiques
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audio_features (
            id INTEGER PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,

            -- lowlevel
            average_loudness REAL,
            
            -- tonal
            chords_changes_rate REAL,
            chords_key TEXT,
            chords_number_rate REAL,
            chords_scale TEXT,

            -- rhythm
            rhythm_danceability REAL,
            beats_count INTEGER,
            bpm REAL,
            beats_loudness_mean REAL,

            -- highlevel - danceability
            danceable TEXT,
            danceability REAL,

            -- highlevel - gender
            gender TEXT,
            gender_probability REAL,

            -- highlevel - genres
            genre TEXT,
            -- dortmund
            genre_dortmund TEXT,
            genre_dortmund_probability REAL,
            genre_dortmund_alternative REAL,
            genre_dortmund_blues REAL,
            genre_dortmund_electronic REAL,
            genre_dortmund_folkcountry REAL,
            genre_dortmund_funksoulrnb REAL,
            genre_dortmund_jazz REAL,
            genre_dortmund_pop REAL,
            genre_dortmund_raphiphop REAL,
            genre_dortmund_rock REAL,
            -- electronic
            genre_electronic TEXT,
            genre_electronic_probability REAL,
            genre_electronic_ambient REAL,
            genre_electronic_dnb REAL,
            genre_electronic_house REAL,
            genre_electronic_techno REAL,
            genre_electronic_trance REAL,
            -- rosamerica
            genre_rosamerica TEXT,
            genre_rosamerica_probability REAL,
            genre_rosamerica_cla REAL,
            genre_rosamerica_dan REAL,
            genre_rosamerica_hip REAL,
            genre_rosamerica_jaz REAL,
            genre_rosamerica_pop REAL,
            genre_rosamerica_roc REAL,
            genre_rosamerica_rhy REAL,
            genre_rosamerica_spe REAL,
            -- tzanetakis            
            genre_tzanetakis TEXT,
            genre_tzanetakis_probability REAL,
            genre_tzanetakis_blu REAL,
            genre_tzanetakis_cla REAL,
            genre_tzanetakis_cou REAL,
            genre_tzanetakis_dis REAL,
            genre_tzanetakis_hip REAL,
            genre_tzanetakis_jaz REAL,
            genre_tzanetakis_met REAL,
            genre_tzanetakis_pop REAL,
            genre_tzanetakis_reg REAL,
            genre_tzanetakis_roc REAL,

            -- highlevel - ismir04
            ismir04_rhythm TEXT,
            ismir04_rhythm_probability REAL,

            -- highlevel - moods
            mood_acoustic TEXT,
            mood_acoustic_probability REAL,
            mood_aggressive TEXT,
            mood_aggressive_probability REAL,
            mood_electronic TEXT,
            mood_electronic_probability REAL,
            mood_happy TEXT,
            mood_happy_probability REAL,
            mood_party TEXT,
            mood_party_probability REAL,
            mood_relaxed TEXT,
            mood_relaxed_probability REAL,
            mood_sad TEXT,
            mood_sad_probability REAL,
            moods_mirex TEXT,
            moods_mirex_probability REAL,

            -- highlevel - autres
            timbre TEXT,
            timbre_probability REAL,
            tonal_atonal TEXT,
            tonal_atonal_probability REAL,
            voice_instrumental TEXT,
            voice_instrumental_probability REAL,

            -- features pour energy_level
            spectral_centroid REAL,
            spectral_flux REAL,
            spectral_complexity REAL,
            spectral_energy REAL,
            zerocrossingrate REAL,
            dynamic_complexity REAL,
            
            -- features pour la key
            key_edma TEXT, 
            scale_edma TEXT,
            strength_edma REAL,
            key_krumhansl TEXT, 
            scale_krumhansl TEXT,
            strength_krumhansl REAL,
            key_temperley TEXT, 
            scale_temperley TEXT,
            strength_temperley REAL,
            
            mood TEXT,
            energy_level INTEGER,
            beat_intensity REAL,
            rg_track_gain REAL,
            initial_key TEXT,
            mood_emb_1 FLOAT,
            mood_emb_2 FLOAT
        );
        """)
        
        # Table de liens morceaux <-> groupes
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS track_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            group_name TEXT NOT NULL,
            added_at TEXT,
            FOREIGN KEY(track_id) REFERENCES tracks(id)
        );
        """)

        # Table de liens morceaux <-> mix
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS track_mix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            mix_name TEXT NOT NULL,
            added_at TEXT,
            FOREIGN KEY(track_id) REFERENCES tracks(id)
        );
        """)

        # Table des transpositions harmoniques et rythmiques
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS track_transpositions (
        id INTEGER PRIMARY KEY,
        key_minus_12 TEXT,
        key_minus_11 TEXT,
        key_minus_10 TEXT,
        key_minus_9 TEXT,
        key_minus_8 TEXT,
        key_minus_7 TEXT,
        key_minus_6 TEXT,
        key_minus_5 TEXT,
        key_minus_4 TEXT,
        key_minus_3 TEXT,
        key_minus_2 TEXT,
        key_minus_1 TEXT,
        key_0 TEXT,
        key_plus_1 TEXT,
        key_plus_2 TEXT,
        key_plus_3 TEXT,
        key_plus_4 TEXT,
        key_plus_5 TEXT,
        key_plus_6 TEXT,
        key_plus_7 TEXT,
        key_plus_8 TEXT,
        key_plus_9 TEXT,
        key_plus_10 TEXT,
        key_plus_11 TEXT,
        key_plus_12 TEXT,
        bpm_minus_12 REAL,
        bpm_minus_11 REAL,
        bpm_minus_10 REAL,
        bpm_minus_9 REAL,
        bpm_minus_8 REAL,
        bpm_minus_7 REAL,
        bpm_minus_6 REAL,
        bpm_minus_5 REAL,
        bpm_minus_4 REAL,
        bpm_minus_3 REAL,
        bpm_minus_2 REAL,
        bpm_minus_1 REAL,
        bpm_0 REAL,
        bpm_plus_1 REAL,
        bpm_plus_2 REAL,
        bpm_plus_3 REAL,
        bpm_plus_4 REAL,
        bpm_plus_5 REAL,
        bpm_plus_6 REAL,
        bpm_plus_7 REAL,
        bpm_plus_8 REAL,
        bpm_plus_9 REAL,
        bpm_plus_10 REAL,
        bpm_plus_11 REAL,
        bpm_plus_12 REAL,
        FOREIGN KEY(id) REFERENCES tracks(id)
        );
        """)

        conn.commit()
        print(f"✅ Base initialisée : {BEETS_DB}")

if __name__ == "__main__":
    create_tables()
