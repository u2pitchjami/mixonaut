# from __future__ import annotations

# from dataclasses import dataclass, field, asdict
# from datetime import datetime
# import sqlite3
# from typing import Any, Optional, TypedDict

# # ---------------------------------------------------------------------------
# # Dataclass correspondant à la table SQLite `audio_features`
# # - Types mappés :
# #   * INTEGER -> int (nullable => int | None)
# #   * REAL/FLOAT -> float | None
# #   * TEXT -> str | None
# #   * TIMESTAMP -> datetime | None (si tu stockes en texte, on peut garder str | None)
# # - Tous les champs (sauf id) sont optionnels pour refléter la DB.
# # ---------------------------------------------------------------------------


# @dataclass(slots=True)
# class AudioFeatures:
#     id: int

#     essentia_status: Optional[str] = None
#     last_error: Optional[str] = None
#     updated_at: Optional[str] = None
#     retries: Optional[int] = None

#     # lowlevel
#     average_loudness: Optional[float] = None

#     # tonal
#     chords_changes_rate: Optional[float] = None
#     chords_key: Optional[str] = None
#     chords_number_rate: Optional[float] = None
#     chords_scale: Optional[str] = None

#     # rhythm
#     rhythm_danceability: Optional[float] = None
#     beats_count: Optional[int] = None
#     bpm: Optional[float] = None
#     beats_loudness_mean: Optional[float] = None
#     onset_rate: Optional[float] = None
#     blbr_mean_b1: Optional[float] = None
#     blbr_mean_b2: Optional[float] = None
#     blbr_mean_b3: Optional[float] = None
#     blbr_mean_b4: Optional[float] = None
#     blbr_mean_b5: Optional[float] = None
#     blbr_mean_b6: Optional[float] = None

#     # highlevel - danceability
#     danceable: Optional[str] = None
#     danceability: Optional[float] = None

#     # highlevel - gender
#     gender: Optional[str] = None
#     gender_probability: Optional[float] = None

#     # highlevel - genres (global)
#     genre: Optional[str] = None

#     # dortmund
#     genre_dortmund: Optional[str] = None
#     genre_dortmund_probability: Optional[float] = None
#     genre_dortmund_alternative: Optional[float] = None
#     genre_dortmund_blues: Optional[float] = None
#     genre_dortmund_electronic: Optional[float] = None
#     genre_dortmund_folkcountry: Optional[float] = None
#     genre_dortmund_funksoulrnb: Optional[float] = None
#     genre_dortmund_jazz: Optional[float] = None
#     genre_dortmund_pop: Optional[float] = None
#     genre_dortmund_raphiphop: Optional[float] = None
#     genre_dortmund_rock: Optional[float] = None

#     # electronic
#     genre_electronic: Optional[str] = None
#     genre_electronic_probability: Optional[float] = None
#     genre_electronic_ambient: Optional[float] = None
#     genre_electronic_dnb: Optional[float] = None
#     genre_electronic_house: Optional[float] = None
#     genre_electronic_techno: Optional[float] = None
#     genre_electronic_trance: Optional[float] = None

#     # rosamerica
#     genre_rosamerica: Optional[str] = None
#     genre_rosamerica_probability: Optional[float] = None
#     genre_rosamerica_cla: Optional[float] = None
#     genre_rosamerica_dan: Optional[float] = None
#     genre_rosamerica_hip: Optional[float] = None
#     genre_rosamerica_jaz: Optional[float] = None
#     genre_rosamerica_pop: Optional[float] = None
#     genre_rosamerica_roc: Optional[float] = None
#     genre_rosamerica_rhy: Optional[float] = None
#     genre_rosamerica_spe: Optional[float] = None

#     # tzanetakis
#     genre_tzanetakis: Optional[str] = None
#     genre_tzanetakis_probability: Optional[float] = None
#     genre_tzanetakis_blu: Optional[float] = None
#     genre_tzanetakis_cla: Optional[float] = None
#     genre_tzanetakis_cou: Optional[float] = None
#     genre_tzanetakis_dis: Optional[float] = None
#     genre_tzanetakis_hip: Optional[float] = None
#     genre_tzanetakis_jaz: Optional[float] = None
#     genre_tzanetakis_met: Optional[float] = None
#     genre_tzanetakis_pop: Optional[float] = None
#     genre_tzanetakis_reg: Optional[float] = None
#     genre_tzanetakis_roc: Optional[float] = None

#     # highlevel - ismir04
#     ismir04_rhythm: Optional[str] = None
#     ismir04_rhythm_probability: Optional[float] = None

#     # highlevel - moods
#     mood_acoustic: Optional[str] = None
#     mood_acoustic_probability: Optional[float] = None
#     mood_aggressive: Optional[str] = None
#     mood_aggressive_probability: Optional[float] = None
#     mood_electronic: Optional[str] = None
#     mood_electronic_probability: Optional[float] = None
#     mood_happy: Optional[str] = None
#     mood_happy_probability: Optional[float] = None
#     mood_party: Optional[str] = None
#     mood_party_probability: Optional[float] = None
#     mood_relaxed: Optional[str] = None
#     mood_relaxed_probability: Optional[float] = None
#     mood_sad: Optional[str] = None
#     mood_sad_probability: Optional[float] = None
#     moods_mirex: Optional[str] = None
#     moods_mirex_probability: Optional[float] = None

#     # highlevel - autres
#     timbre: Optional[str] = None
#     timbre_probability: Optional[float] = None
#     tonal_atonal: Optional[str] = None
#     tonal_atonal_probability: Optional[float] = None
#     voice_instrumental: Optional[str] = None
#     voice_instrumental_probability: Optional[float] = None

#     # features pour energy_level
#     spectral_centroid: Optional[float] = None
#     spectral_flux: Optional[float] = None
#     spectral_complexity: Optional[float] = None
#     spectral_energy: Optional[float] = None
#     spectral_rms_mean: Optional[float] = None
#     spectral_rms_stdev: Optional[float] = None
#     zerocrossingrate: Optional[float] = None
#     dynamic_complexity: Optional[float] = None

#     # features pour la key (trois algos)
#     key_edma: Optional[str] = None
#     scale_edma: Optional[str] = None
#     strength_edma: Optional[float] = None
#     key_krumhansl: Optional[str] = None
#     scale_krumhansl: Optional[str] = None
#     strength_krumhansl: Optional[float] = None
#     key_temperley: Optional[str] = None
#     scale_temperley: Optional[str] = None
#     strength_temperley: Optional[float] = None

#     # agrégés/auxiliaires
#     mood: Optional[str] = None
#     duration: Optional[float] = None
#     beat_intensity: Optional[float] = None
#     rg_track_gain: Optional[float] = None
#     initial_key: Optional[str] = None
#     mood_emb_1: Optional[float] = None
#     mood_emb_2: Optional[float] = None
#     genre_emb_1: Optional[float] = None
#     genre_emb_2: Optional[float] = None

#     # ------------ Helpers de conversion DB ↔ dataclass ------------

#     @staticmethod
#     def _to_datetime(value: Any) -> Optional[datetime]:
#         if value is None:
#             return None
#         if isinstance(value, datetime):
#             return value
#         # Si stocké en texte (ISO), essaie de parser ; à adapter si autre format
#         try:
#             return datetime.fromisoformat(str(value))
#         except Exception:
#             return None

#     @classmethod
#     def from_row(cls, row: sqlite3.Row | dict[str, Any]) -> "AudioFeatures":
#         """Crée un `AudioFeatures` depuis une row (sqlite3.Row ou dict).
#         Suppose que les clés/colonnes portent les mêmes noms que les attributs.
#         """
#         get = row.__getitem__ if isinstance(row, sqlite3.Row) else row.get
#         return cls(
#             id=int(get("id")),
#             essentia_status=get("essentia_status"),
#             last_error=get("last_error"),
#             updated_at=cls._to_datetime(get("updated_at")),
#             retries=(int(get("retries")) if get("retries") is not None else None),
#             average_loudness=get("average_loudness"),
#             chords_changes_rate=get("chords_changes_rate"),
#             chords_key=get("chords_key"),
#             chords_number_rate=get("chords_number_rate"),
#             chords_scale=get("chords_scale"),
#             rhythm_danceability=get("rhythm_danceability"),
#             beats_count=(int(get("beats_count")) if get("beats_count") is not None else None),
#             bpm=get("bpm"),
#             beats_loudness_mean=get("beats_loudness_mean"),
#             onset_rate=get("onset_rate"),
#             blbr_mean_b1=get("blbr_mean_b1"),
#             blbr_mean_b2=get("blbr_mean_b2"),
#             blbr_mean_b3=get("blbr_mean_b3"),
#             blbr_mean_b4=get("blbr_mean_b4"),
#             blbr_mean_b5=get("blbr_mean_b5"),
#             blbr_mean_b6=get("blbr_mean_b6"),
#             danceable=get("danceable"),
#             danceability=get("danceability"),
#             gender=get("gender"),
#             gender_probability=get("gender_probability"),
#             genre=get("genre"),
#             genre_dortmund=get("genre_dortmund"),
#             genre_dortmund_probability=get("genre_dortmund_probability"),
#             genre_dortmund_alternative=get("genre_dortmund_alternative"),
#             genre_dortmund_blues=get("genre_dortmund_blues"),
#             genre_dortmund_electronic=get("genre_dortmund_electronic"),
#             genre_dortmund_folkcountry=get("genre_dortmund_folkcountry"),
#             genre_dortmund_funksoulrnb=get("genre_dortmund_funksoulrnb"),
#             genre_dortmund_jazz=get("genre_dortmund_jazz"),
#             genre_dortmund_pop=get("genre_dortmund_pop"),
#             genre_dortmund_raphiphop=get("genre_dortmund_raphiphop"),
#             genre_dortmund_rock=get("genre_dortmund_rock"),
#             genre_electronic=get("genre_electronic"),
#             genre_electronic_probability=get("genre_electronic_probability"),
#             genre_electronic_ambient=get("genre_electronic_ambient"),
#             genre_electronic_dnb=get("genre_electronic_dnb"),
#             genre_electronic_house=get("genre_electronic_house"),
#             genre_electronic_techno=get("genre_electronic_techno"),
#             genre_electronic_trance=get("genre_electronic_trance"),
#             genre_rosamerica=get("genre_rosamerica"),
#             genre_rosamerica_probability=get("genre_rosamerica_probability"),
#             genre_rosamerica_cla=get("genre_rosamerica_cla"),
#             genre_rosamerica_dan=get("genre_rosamerica_dan"),
#             genre_rosamerica_hip=get("genre_rosamerica_hip"),
#             genre_rosamerica_jaz=get("genre_rosamerica_jaz"),
#             genre_rosamerica_pop=get("genre_rosamerica_pop"),
#             genre_rosamerica_roc=get("genre_rosamerica_roc"),
#             genre_rosamerica_rhy=get("genre_rosamerica_rhy"),
#             genre_rosamerica_spe=get("genre_rosamerica_spe"),
#             genre_tzanetakis=get("genre_tzanetakis"),
#             genre_tzanetakis_probability=get("genre_tzanetakis_probability"),
#             genre_tzanetakis_blu=get("genre_tzanetakis_blu"),
#             genre_tzanetakis_cla=get("genre_tzanetakis_cla"),
#             genre_tzanetakis_cou=get("genre_tzanetakis_cou"),
#             genre_tzanetakis_dis=get("genre_tzanetakis_dis"),
#             genre_tzanetakis_hip=get("genre_tzanetakis_hip"),
#             genre_tzanetakis_jaz=get("genre_tzanetakis_jaz"),
#             genre_tzanetakis_met=get("genre_tzanetakis_met"),
#             genre_tzanetakis_pop=get("genre_tzanetakis_pop"),
#             genre_tzanetakis_reg=get("genre_tzanetakis_reg"),
#             genre_tzanetakis_roc=get("genre_tzanetakis_roc"),
#             ismir04_rhythm=get("ismir04_rhythm"),
#             ismir04_rhythm_probability=get("ismir04_rhythm_probability"),
#             mood_acoustic=get("mood_acoustic"),
#             mood_acoustic_probability=get("mood_acoustic_probability"),
#             mood_aggressive=get("mood_aggressive"),
#             mood_aggressive_probability=get("mood_aggressive_probability"),
#             mood_electronic=get("mood_electronic"),
#             mood_electronic_probability=get("mood_electronic_probability"),
#             mood_happy=get("mood_happy"),
#             mood_happy_probability=get("mood_happy_probability"),
#             mood_party=get("mood_party"),
#             mood_party_probability=get("mood_party_probability"),
#             mood_relaxed=get("mood_relaxed"),
#             mood_relaxed_probability=get("mood_relaxed_probability"),
#             mood_sad=get("mood_sad"),
#             mood_sad_probability=get("mood_sad_probability"),
#             moods_mirex=get("moods_mirex"),
#             moods_mirex_probability=get("moods_mirex_probability"),
#             timbre=get("timbre"),
#             timbre_probability=get("timbre_probability"),
#             tonal_atonal=get("tonal_atonal"),
#             tonal_atonal_probability=get("tonal_atonal_probability"),
#             voice_instrumental=get("voice_instrumental"),
#             voice_instrumental_probability=get("voice_instrumental_probability"),
#             spectral_centroid=get("spectral_centroid"),
#             spectral_flux=get("spectral_flux"),
#             spectral_complexity=get("spectral_complexity"),
#             spectral_energy=get("spectral_energy"),
#             spectral_rms_mean=get("spectral_rms_mean"),
#             spectral_rms_stdev=get("spectral_rms_stdev"),
#             zerocrossingrate=get("zerocrossingrate"),
#             dynamic_complexity=get("dynamic_complexity"),
#             key_edma=get("key_edma"),
#             scale_edma=get("scale_edma"),
#             strength_edma=get("strength_edma"),
#             key_krumhansl=get("key_krumhansl"),
#             scale_krumhansl=get("scale_krumhansl"),
#             strength_krumhansl=get("strength_krumhansl"),
#             key_temperley=get("key_temperley"),
#             scale_temperley=get("scale_temperley"),
#             strength_temperley=get("strength_temperley"),
#             mood=get("mood"),
#             duration=get("duration"),
#             beat_intensity=get("beat_intensity"),
#             rg_track_gain=get("rg_track_gain"),
#             initial_key=get("initial_key"),
#             mood_emb_1=get("mood_emb_1"),
#             mood_emb_2=get("mood_emb_2"),
#             genre_emb_1=get("genre_emb_1"),
#             genre_emb_2=get("genre_emb_2"),
#         )

#     def to_row(self) -> dict[str, Any]:
#         """Convertit en dict prêt pour SQLite (sérialisation simple).
#         `updated_at` est converti en ISO 8601 si datetime.
#         """
#         data = asdict(self)
#         if self.updated_at is not None:
#             data["updated_at"] = self.updated_at.isoformat()
#         return data


# # TypedDict pour utilisation côté frontières (facultatif)
# class AudioFeaturesRow(TypedDict, total=False):
#     id: int
#     essentia_status: str | None
#     last_error: str | None
#     updated_at: str | None
#     retries: int | None
#     average_loudness: float | None
#     chords_changes_rate: float | None
#     chords_key: str | None
#     chords_number_rate: float | None
#     chords_scale: str | None
#     rhythm_danceability: float | None
#     beats_count: int | None
#     bpm: float | None
#     beats_loudness_mean: float | None
#     onset_rate: float | None
#     blbr_mean_b1: float | None
#     blbr_mean_b2: float | None
#     blbr_mean_b3: float | None
#     blbr_mean_b4: float | None
#     blbr_mean_b5: float | None
#     blbr_mean_b6: float | None
#     danceable: str | None
#     danceability: float | None
#     gender: str | None
#     gender_probability: float | None
#     genre: str | None
#     genre_dortmund: str | None
#     genre_dortmund_probability: float | None
#     genre_dortmund_alternative: float | None
#     genre_dortmund_blues: float | None
#     genre_dortmund_electronic: float | None
#     genre_dortmund_folkcountry: float | None
#     genre_dortmund_funksoulrnb: float | None
#     genre_dortmund_jazz: float | None
#     genre_dortmund_pop: float | None
#     genre_dortmund_raphiphop: float | None
#     genre_dortmund_rock: float | None
#     genre_electronic: str | None
#     genre_electronic_probability: float | None
#     genre_electronic_ambient: float | None
#     genre_electronic_dnb: float | None
#     genre_electronic_house: float | None
#     genre_electronic_techno: float | None
#     genre_electronic_trance: float | None
#     genre_rosamerica: str | None
#     genre_rosamerica_probability: float | None
#     genre_rosamerica_cla: float | None
#     genre_rosamerica_dan: float | None
#     genre_rosamerica_hip: float | None
#     genre_rosamerica_jaz: float | None
#     genre_rosamerica_pop: float | None
#     genre_rosamerica_roc: float | None
#     genre_rosamerica_rhy: float | None
#     genre_rosamerica_spe: float | None
#     genre_tzanetakis: str | None
#     genre_tzanetakis_probability: float | None
#     genre_tzanetakis_blu: float | None
#     genre_tzanetakis_cla: float | None
#     genre_tzanetakis_cou: float | None
#     genre_tzanetakis_dis: float | None
#     genre_tzanetakis_hip: float | None
#     genre_tzanetakis_jaz: float | None
#     genre_tzanetakis_met: float | None
#     genre_tzanetakis_pop: float | None
#     genre_tzanetakis_reg: float | None
#     genre_tzanetakis_roc: float | None
#     ismir04_rhythm: str | None
#     ismir04_rhythm_probability: float | None
#     mood_acoustic: str | None
#     mood_acoustic_probability: float | None
#     mood_aggressive: str | None
#     mood_aggressive_probability: float | None
#     mood_electronic: str | None
#     mood_electronic_probability: float | None
#     mood_happy: str | None
#     mood_happy_probability: float | None
#     mood_party: str | None
#     mood_party_probability: float | None
#     mood_relaxed: str | None
#     mood_relaxed_probability: float | None
#     mood_sad: str | None
#     mood_sad_probability: float | None
#     moods_mirex: str | None
#     moods_mirex_probability: float | None
#     timbre: str | None
#     timbre_probability: float | None
#     tonal_atonal: str | None
#     tonal_atonal_probability: float | None
#     voice_instrumental: str | None
#     voice_instrumental_probability: float | None
#     spectral_centroid: float | None
#     spectral_flux: float | None
#     spectral_complexity: float | None
#     spectral_energy: float | None
#     spectral_rms_mean: float | None
#     spectral_rms_stdev: float | None
#     zerocrossingrate: float | None
#     dynamic_complexity: float | None
#     key_edma: str | None
#     scale_edma: str | None
#     strength_edma: float | None
#     key_krumhansl: str | None
#     scale_krumhansl: str | None
#     strength_krumhansl: float | None
#     key_temperley: str | None
#     scale_temperley: str | None
#     strength_temperley: float | None
#     mood: str | None
#     duration: float | None
#     beat_intensity: float | None
#     rg_track_gain: float | None
#     initial_key: str | None
#     mood_emb_1: float | None
#     mood_emb_2: float | None
#     genre_emb_1: float | None
#     genre_emb_2: float | None
