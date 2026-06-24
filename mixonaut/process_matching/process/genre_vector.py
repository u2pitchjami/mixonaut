"""
Genre vector utilities for Mixonaut.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import TypeAlias
import sqlite3

GenreVector: TypeAlias = list[float]
GenreRow = sqlite3.Row

GENRE_COLUMNS: tuple[str, ...] = (
    # Dortmund
    "genre_dortmund_alternative",
    "genre_dortmund_blues",
    "genre_dortmund_electronic",
    "genre_dortmund_folkcountry",
    "genre_dortmund_funksoulrnb",
    "genre_dortmund_jazz",
    "genre_dortmund_pop",
    "genre_dortmund_raphiphop",
    "genre_dortmund_rock",
    # Electronic
    "genre_electronic_ambient",
    "genre_electronic_dnb",
    "genre_electronic_house",
    "genre_electronic_techno",
    "genre_electronic_trance",
    # Rosamerica
    "genre_rosamerica_cla",
    "genre_rosamerica_dan",
    "genre_rosamerica_hip",
    "genre_rosamerica_jaz",
    "genre_rosamerica_pop",
    "genre_rosamerica_roc",
    "genre_rosamerica_rhy",
    "genre_rosamerica_spe",
    # Tzanetakis
    "genre_tzanetakis_blu",
    "genre_tzanetakis_cla",
    "genre_tzanetakis_cou",
    "genre_tzanetakis_dis",
    "genre_tzanetakis_hip",
    "genre_tzanetakis_jaz",
    "genre_tzanetakis_met",
    "genre_tzanetakis_pop",
    "genre_tzanetakis_reg",
    "genre_tzanetakis_roc",
)


def get_genre_columns_sql() -> str:
    """
    Retourne les colonnes genre formatées pour une requête SELECT.
    """
    return ", ".join(GENRE_COLUMNS)


def build_genre_vector(row: Mapping[str, object]) -> GenreVector:
    """
    Construit un vecteur genre depuis une ligne SQL.

    Les valeurs NULL sont remplacées par 0.0.
    """
    vector: GenreVector = []

    for column in GENRE_COLUMNS:
        value = row[column]

        if value is None:
            vector.append(0.0)
            continue

        if isinstance(value, int | float | str):
            vector.append(float(value))
            continue

        raise ValueError(f"Valeur genre invalide pour la colonne {column}: {value!r}")
    return vector


def calculate_genre_similarity(
    ref_vector: GenreVector,
    candidate_vector: GenreVector,
) -> float:
    """
    Calcule une similarité cosinus entre deux vecteurs genre.

    Retourne un score entre 0.0 et 1.0.
    """
    if len(ref_vector) != len(candidate_vector):
        raise ValueError(
            "Les vecteurs genre doivent avoir la même dimension: "
            f"{len(ref_vector)} != {len(candidate_vector)}"
        )

    dot_product = sum(
        ref_value * candidate_value
        for ref_value, candidate_value in zip(
            ref_vector,
            candidate_vector,
            strict=True,
        )
    )

    ref_norm = math.sqrt(sum(value * value for value in ref_vector))
    candidate_norm = math.sqrt(sum(value * value for value in candidate_vector))

    if ref_norm == 0.0 or candidate_norm == 0.0:
        return 0.0

    score = dot_product / (ref_norm * candidate_norm)

    return max(0.0, min(1.0, score))
