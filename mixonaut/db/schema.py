"""
2025-08-20.

schema d'initialisation de la base sqlite à faire sur la base beets.
"""

import sqlite3

from mixonaut.utils.config import BEETS_DB


def create_tables():
    """
    2025-08-20.

    schema d'initialisation de la base sqlite à faire sur la base beets.
    """
    with sqlite3.connect(BEETS_DB) as conn:
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_keys = ON;")

        # ITEMS ####
        # 1) champs updated_at
        cursor.execute("ALTER TABLE items ADD COLUMN updated_at TEXT;")
        # 2) index
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_items_path ON items(path);
        """
        )
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_items_artist_album ON items(artist, album);
        """
        )
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_items_genre ON items(genre);
        """
        )
        # 3) Triggers 'updated_at' (SQLite ne permet pas d'assigner NEW.updated_at directement)
        cursor.execute(
            """
        CREATE TRIGGER IF NOT EXISTS trg_items_touch
        AFTER UPDATE ON items
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
            UPDATE items SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END;
        """
        )
        # à l'INSERT : initialise updated_at
        cursor.execute(
            """
        CREATE TRIGGER IF NOT EXISTS trg_items_insert_touch
        AFTER INSERT ON items
        FOR EACH ROW
        BEGIN
        UPDATE items SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END;
        """
        )

        # AUDIO_FEATURES ####
        # 1) Table des features analytiques
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS audio_features (
            id INTEGER PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,
            essentia_status TEXT DEFAULT 'PENDING',
            last_error TEXT,
            updated_at TIMESTAMP,
            retries INTEGER DEFAULT 0,

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
            onset_rate REAL,
            blbr_mean_b1 REAL,
            blbr_mean_b2 REAL,
            blbr_mean_b3 REAL,
            blbr_mean_b4 REAL,
            blbr_mean_b5 REAL,
            blbr_mean_b6 REAL,

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
            spectral_rms_mean REAL,
            spectral_rms_stdev REAL,
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
            duration REAL,
            beat_intensity REAL,
            rg_track_gain REAL,
            initial_key TEXT,
            mood_emb_1 FLOAT,
            mood_emb_2 FLOAT,
            genre_emb_1 FLOAT,
            genre_emb_2 FLOAT
        );
        """
        )

        # 2) Index
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS af_status_idx ON audio_features(essentia_status);
        """
        )
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS af_status_updated_idx ON audio_features(essentia_status, updated_at);
        """
        )

        # 3) Trigger
        cursor.execute(
            """
        CREATE TRIGGER IF NOT EXISTS trg_audio_features_touch
        AFTER UPDATE ON audio_features
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
            UPDATE audio_features
            SET updated_at = CURRENT_TIMESTAMP
            WHERE rowid = NEW.rowid;
        END;
        """
        )

        # AUDIO_HASH ####
        # 1) Empreintes par contenu fichier
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS audio_hash (
            id   INTEGER PRIMARY KEY,                                  -- items.id (Beets)
            file_sha1  TEXT NOT NULL,
            audio_hash_sha256    TEXT NOT NULL,
            fingerprint          TEXT NOT NULL,                             -- empreinte Chromaprint (chaine d'entiers)
            duration             INTEGER,                                    -- durée rapportée par fpcalc (s)
            chromaprint_version  INTEGER,                                    -- version libchromaprint si dispo
            acoustid_id          TEXT,                                       -- UUID AcoustID si lookup (optionnel)
            confidence           REAL,                                       -- confiance AcoustID (optionnel)
            status     TEXT,
            last_error TEXT,                                                 -- message d'erreur si échec
            created_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
        )
        # 2) Index
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_audio_hash_file_sha1 ON audio_hash(file_sha1);
        """
        )
        # Si tu fais des matches via hash audio “fort”
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_audio_hash_sha256 ON audio_hash(audio_hash_sha256);
        """
        )
        # Si tu relies aussi via fingerprint (Chromaprint)
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_audio_hash_fingerprint ON audio_hash(fingerprint);
        """
        )
        # Recherches par statut + fraîcheur (file d’attente / reprocessing)
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_audio_hash_status_updated
        ON audio_hash(status, updated_at);
        """
        )
        # Si tu filtres souvent “erreurs récentes”
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_audio_hash_status_created
        ON audio_hash(status, created_at);
        """
        )

        # 3) Trigger
        cursor.execute(
            """
        CREATE TRIGGER IF NOT EXISTS trg_audio_hash_touch
        AFTER UPDATE ON audio_hash
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
            UPDATE audio_hash SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END;
        """
        )

        # TRANSPOSITION ###

        # 1) Table des transpositions harmoniques et rythmiques
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS track_transpositions (
        id INTEGER PRIMARY KEY,
        transposition_status TEXT DEFAULT 'PENDING'
        last_error TEXT,
        last_error TEXT,
        updated_at TIMESTAMP,
        retries INTEGER DEFAULT 0,
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
        """
        )

        # 2) Trigger
        cursor.execute(
            """
        CREATE TRIGGER IF NOT EXISTS trg_track_transpositions_touch
        AFTER UPDATE ON track_transpositions
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
            UPDATE track_transpositions
            SET updated_at = CURRENT_TIMESTAMP
            WHERE rowid = NEW.rowid;
        END;
        """
        )

        # IMPORTED_FILES ####

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS imported_files (
            id INTEGER PRIMARY KEY,
            path TEXT,                         -- chemin relatif qBit du fichier
            name TEXT,                         -- nom de fichier
            size INTEGER,
            last_seen TIMESTAMP,
            imported_in_beets_at TEXT,         -- NULL si pas encore importé
            torrent_hash TEXT,
            torrent_name TEXT,
            torrent_added_on INTEGER,
            torrent_completion_on INTEGER,
            torrent_ratio REAL,
            auto_cleaned BOOLEAN DEFAULT 0,
            staged_for_import_at TEXT,         -- date de copie/extraction vers imports
            staging_error TEXT,                -- message d'erreur en staging
            torrent_save_path TEXT,            -- chemin source qBit (absolu)
            album_rel_dir TEXT                 -- dossier relatif de l’album sous imports (parent(path))
        );
        """
        )

        # 2) Index
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS ux_imported_files_hash_path_name
        ON imported_files(torrent_hash, path, name);
        """
        )
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS ix_imported_files_hash ON imported_files(torrent_hash);
        """
        )
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS ix_imported_files_imported_at
        ON imported_files(imported_in_beets_at);
        """
        )
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS ix_imported_files_album_rel_dir
        ON imported_files(album_rel_dir);
        """
        )
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS ix_imported_files_not_imported
        ON imported_files(imported_in_beets_at) WHERE imported_in_beets_at IS NULL;
        """
        )
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS ix_imported_files_staged_null
        ON imported_files(staged_for_import_at) WHERE staged_for_import_at IS NULL;
        """
        )
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS ix_tdec_decision
        ON torrent_decisions(decision);
        """
        )

        # TRACK_GROUPS ####

        # Table de liens morceaux <-> groupes
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS track_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            group_name TEXT NOT NULL,
            added_at TEXT,
            FOREIGN KEY(track_id) REFERENCES tracks(id)
        );
        """
        )

        # TRACK_MIX ####

        # Table de liens morceaux <-> mix
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS track_mix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            mix_name TEXT NOT NULL,
            added_at TEXT,
            FOREIGN KEY(track_id) REFERENCES tracks(id)
        );
        """
        )

        # V_ANALYSE ####

        cursor.execute(
            """
        DROP VIEW IF EXISTS "main"."v_analyse";
        CREATE VIEW v_analyse AS
        SELECT
            i.id,
            i.artist,
            i.title,
            i.album,
            i.genre,
            i.bpm,
            a.mood,
            a.beat_intensity,
            i.rg_track_gain,
            i.initial_key,
            i.path,
            i.updated_at AS beets_updated_at,
            a.essentia_status,
            a.last_error AS essentia_last_error,
            a.updated_at AS essentia_updated_at,
            f.status AS hash_status,
            f.last_error AS hash_last_error,
            f.updated_at AS hash_last_updated_at,
            t.transposition_status,
            t.last_error AS transposition_last_error,
            t.updated_at AS transposition_updated_at
        FROM items AS i
        JOIN audio_features AS a USING (id)
        JOIN track_transpositions AS t USING (id)
        JOIN audio_hash AS f USING (id)
        """
        )

        # v_needs_manual ####

        cursor.execute(
            """
        DROP VIEW IF EXISTS "v_needs_manual";
        CREATE VIEW v_needs_manual AS
        SELECT
        ts.torrent_hash,
        ts.torrent_name,
        ts.decision,
        ts.ratio,
        ts.age_days,
        ts.since_decision_days,
        datetime(ts.added_on, 'unixepoch') AS added_on_dt
        FROM v_torrent_status ts
        WHERE ts.imported_at IS NULL
        AND ts.decision IN ('NEEDS_MANUAL','DUPLICATE_SOFT')
        ORDER BY ts.since_decision_days DESC NULLS LAST, ts.age_days DESC, ts.torrent_name
        """
        )

        # v_ready_for_deletion ####

        cursor.execute(
            """
        DROP VIEW IF EXISTS "v_ready_for_deletion";
        CREATE VIEW v_ready_for_deletion AS
        SELECT
        ts.torrent_hash,
        ts.torrent_name,
        ts.decision,
        ts.ratio,
        ts.age_days,
        ts.since_decision_days,
        datetime(ts.added_on, 'unixepoch') AS added_on_dt,
        datetime(ts.completed_on, 'unixepoch') AS completed_on_dt,
        ts.imported_at
        FROM v_torrent_status ts
        WHERE
        (ts.ratio >= 2.0 OR ts.age_days >= 30)
        AND (
            ts.imported_at IS NOT NULL
            OR ts.decision IN ('REJECT','DUPLICATE_HARD','REPLACED')
            OR (ts.decision IN ('NEEDS_MANUAL','DUPLICATE_SOFT') AND ts.since_decision_days >= 14)
        )
        ORDER BY ts.completed_on DESC NULLS LAST, ts.torrent_name
                """
        )

        # v_rejected ####

        cursor.execute(
            """
        DROP VIEW IF EXISTS "v_rejected";
        CREATE VIEW v_rejected AS
        SELECT
        ts.torrent_hash,
        ts.torrent_name,
        ts.decision,
        ts.ratio,
        ts.age_days,
        datetime(ts.added_on, 'unixepoch') AS added_on_dt,
        ts.decided_at
        FROM v_torrent_status ts
        WHERE ts.imported_at IS NULL
        AND ts.decision IN ('REJECT','DUPLICATE_HARD','REPLACED')
        ORDER BY ts.age_days DESC, ts.torrent_name
        """
        )

        # v_torrent_base ####

        cursor.execute(
            """
        DROP VIEW IF EXISTS "v_torrent_base";
        CREATE VIEW v_torrent_base AS
        SELECT
        ifs.torrent_hash,
        MAX(ifs.torrent_name) AS torrent_name,
        MAX(ifs.torrent_ratio) AS ratio,
        MAX(ifs.torrent_added_on) AS added_on,
        MAX(ifs.torrent_completion_on) AS completed_on,
        MAX(ifs.imported_in_beets_at) AS imported_at,
        MAX(ifs.auto_cleaned) AS any_cleaned
        FROM imported_files ifs
        GROUP BY ifs.torrent_hash
                """
        )

        # v_torrent_status ####

        cursor.execute(
            """
        DROP VIEW IF EXISTS "v_torrent_status";
        CREATE VIEW v_torrent_status AS
        SELECT
        b.torrent_hash,
        b.torrent_name,
        b.ratio,
        b.added_on,
        b.completed_on,
        b.imported_at,
        COALESCE(d.decision, 'PENDING') AS decision,
        d.reason,
        d.decided_at,
        (julianday('now') - julianday(datetime(b.added_on, 'unixepoch'))) AS age_days,
        CASE WHEN d.decided_at IS NOT NULL
            THEN (julianday('now') - julianday(d.decided_at)) ELSE NULL END AS since_decision_days
        FROM v_torrent_base b
        LEFT JOIN torrent_decisions d ON d.torrent_hash = b.torrent_hash
                """
        )

        # v_torrents_autoclean ####

        cursor.execute(
            """
        DROP VIEW IF EXISTS "v_torrents_autoclean";
        CREATE VIEW v_torrents_autoclean AS
        SELECT DISTINCT ifs.torrent_name, ifs.torrent_hash
        FROM imported_files ifs
        JOIN torrent_decisions td ON td.torrent_hash = ifs.torrent_hash
        WHERE td.decision IN ('REJECT','DUPLICATE_HARD','REPLACED')
        AND ifs.imported_in_beets_at IS NULL
                """
        )

        conn.commit()
        print(f"✅ Base initialisée : {BEETS_DB}")


if __name__ == "__main__":
    create_tables()
