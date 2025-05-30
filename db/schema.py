import sqlite3
from pathlib import Path
from utils.config import MIX_DB

def create_tables():
    with sqlite3.connect(MIX_DB) as conn:
        cursor = conn.cursor()
        print(MIX_DB)
        # Table principale des morceaux
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beet_id TEXT UNIQUE,
            track_uid TEXT NOT NULL UNIQUE,
            present_in_beets INTEGER,
            title TEXT,
            artist TEXT,
            album TEXT,
            path TEXT,
            bpm INTEGER,
            key TEXT,
            rg_gain REAL,
            genre TEXT,
            length REAL,
            mood TEXT,
            energy_level INTEGER,
            beat_intensity REAL,
            essentia_genres TEXT,
            mood_emb_1 FLOAT,
            mood_emb_2 FLOAT,
            added_at TEXT,
            updated_at TEXT
        );
        """)

        # Table des features analytiques
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audio_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,

            -- lowlevel
            average_loudness REAL,
            rg_gain REAL,

            -- tonal
            chords_changes_rate REAL,
            chords_key TEXT,
            chords_number_rate REAL,
            chords_scale TEXT,

            -- rhythm
            rhythm_danceability REAL,
            beats_count INTEGER,
            bpm_essentia REAL,
            beats_loudness_mean REAL,

            -- highlevel - danceability
            danceable TEXT,
            danceability REAL,

            -- highlevel - gender
            gender TEXT,
            gender_probability REAL,

            -- highlevel - genres
            genre_dortmund TEXT,
            genre_dortmund_probability REAL,
            genre_electronic TEXT,
            genre_electronic_probability REAL,
            genre_rosamerica TEXT,
            genre_rosamerica_probability REAL,
            genre_tzanetakis TEXT,
            genre_tzanetakis_probability REAL,

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
            strength_temperley REAL
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
            track_id INTEGER PRIMARY KEY,
            key_minus_12 TEXT,
            key_minus_9 TEXT,
            key_minus_6 TEXT,
            key_minus_3 TEXT,
            key_0 TEXT,
            key_plus_3 TEXT,
            key_plus_6 TEXT,
            key_plus_9 TEXT,
            key_plus_12 TEXT,
            bpm_minus_12 REAL,
            bpm_minus_9 REAL,
            bpm_minus_6 REAL,
            bpm_minus_3 REAL,
            bpm_0 REAL,
            bpm_plus_3 REAL,
            bpm_plus_6 REAL,
            bpm_plus_9 REAL,
            bpm_plus_12 REAL,
            FOREIGN KEY(track_id) REFERENCES tracks(id)
        );
        """)

        conn.commit()
        print(f"✅ Base initialisée : {MIX_DB}")

if __name__ == "__main__":
    create_tables()
