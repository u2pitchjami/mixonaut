from __future__ import annotations


from mixonaut.db.access import select_all
from mixonaut.process_matching.models.matching import GENRE_BPM_RANGES
from mixonaut.process_matching.param.weights import WEIGHT_PROFILES
import argparse
import subprocess
from mixonaut.utils.logger import get_logger
from typing import Any
import sqlite3

logger = get_logger("Generate_Compatible_Tracks")


GENRE_CHOICES = list(GENRE_BPM_RANGES.keys())
WEIGHTS_CHOICES = list(WEIGHT_PROFILES.keys())


def build_matching_command(
    track_id: int,
    options: dict[str, str | int | bool | None],
) -> list[str]:
    command = [
        "python",
        "mixonaut/scripts/matching/run_tracks_matching.py",
        "--track-id",
        str(track_id),
        "--max-results",
        str(options["max_results"]),
        "--weights-type",
        str(options["weights_type"]),
    ]

    if options["target_bpm"] is not None:
        command.extend(["--target-bpm", str(options["target_bpm"])])

    if options["genre"]:
        command.extend(["--genre", str(options["genre"])])

    if options["artist"]:
        command.extend(["--artist", str(options["artist"])])

    if options["label"]:
        command.extend(["--label", str(options["label"])])

    if options["year_min"] is not None:
        command.extend(["--year-min", str(options["year_min"])])

    if options["year_max"] is not None:
        command.extend(["--year-max", str(options["year_max"])])

    if options["grouped"]:
        command.append("--grouped")

    if options["include_live"]:
        command.append("--include-live")

    return command


def ask_choice(
    title: str, choices: list[str], default: str | None = None
) -> str | None:
    print(f"\n=== {title} ===")

    for index, choice in enumerate(choices, start=1):
        extra = ""

        if title == "Genre":
            genre_range = GENRE_BPM_RANGES[choice]
            extra = f" ({genre_range.min_bpm}-{genre_range.max_bpm} BPM)"

        print(f"{index}. {choice}{extra}")

    default_text = f" [{default}]" if default else " [vide]"
    raw_choice = input(f"\nChoix{default_text} : ").strip()

    if not raw_choice:
        return default

    try:
        selected_index = int(raw_choice)
    except ValueError:
        print("Choix invalide, valeur par défaut utilisée.")
        return default

    if 1 <= selected_index <= len(choices):
        return choices[selected_index - 1]

    print("Choix hors limite, valeur par défaut utilisée.")
    return default


def ask_optional_float(
    label: str,
    default: float | int | None = None,
) -> float | None:
    default_text = f" [{default}]" if default is not None else " [vide]"

    raw_value = input(f"{label}{default_text} : ").strip()

    if not raw_value:
        return float(default) if default is not None else None

    try:
        return float(raw_value)
    except ValueError:
        print(f"Valeur invalide pour {label}, ignorée.")
        return default


def ask_optional_int(label: str) -> int | None:
    raw_value = input(f"{label} [vide] : ").strip()

    if not raw_value:
        return None

    try:
        return int(raw_value)
    except ValueError:
        print(f"Valeur invalide pour {label}, ignorée.")
        return None


def ask_flow_options(default_bpm: float | None) -> dict[str, Any]:
    print("\n=== Options du matching ===")

    target_bpm = ask_optional_float("Target BPM", default=default_bpm)
    max_results = ask_optional_int("Max results") or 50

    weights_type = ask_choice(
        title="Weights type",
        choices=WEIGHTS_CHOICES,
        default="standard",
    )

    genre = ask_choice(
        title="Genre",
        choices=GENRE_CHOICES,
        default="all",
    )

    artist = input("Artist [vide] : ").strip()
    label = input("Label [vide] : ").strip()

    year_min = ask_optional_int("Year min")
    year_max = ask_optional_int("Year max")

    grouped_raw = input("Grouped ? [Y/n] : ").strip().lower()
    grouped = grouped_raw not in {"n", "no", "0", "false"}

    include_live_raw = input("Include live ? [y/N] : ").strip().lower()
    include_live = include_live_raw in {"y", "yes", "1", "true"}

    return {
        "target_bpm": target_bpm,
        "max_results": max_results,
        "weights_type": weights_type,
        "genre": genre,
        "artist": artist,
        "label": label,
        "year_min": year_min,
        "year_max": year_max,
        "grouped": grouped,
        "include_live": include_live,
    }


def search_tracks(query: str) -> list[sqlite3.Row]:
    sql = """
        SELECT
            items.id,
            items.artist,
            items.title,
            items.album,
            audio_features.genre,
            audio_features.bpm,
            audio_features.beat_intensity
        FROM items
        LEFT JOIN audio_features
            ON audio_features.id = items.id
        WHERE items.title LIKE ? COLLATE NOCASE
           OR items.artist LIKE ? COLLATE NOCASE
           OR (items.artist || ' ' || items.title) LIKE ? COLLATE NOCASE
           OR (items.title || ' ' || items.artist) LIKE ? COLLATE NOCASE
        ORDER BY items.artist, items.title
        LIMIT 50
    """

    like_query = f"%{query}%"

    rows = select_all(
        sql,
        params=(like_query, like_query, like_query, like_query),
        logger=logger,
    )
    return rows


def choose_track(results: list[sqlite3.Row]) -> sqlite3.Row:
    if not results:
        raise RuntimeError("Aucun résultat trouvé.")

    for index, row in enumerate(results, start=1):
        track_id, artist, title, album, genre, bpm, beat_intensity = row

        print(
            f"{index}. [{track_id}] "
            f"{artist} - {title} "
            f"({album}) | "
            f"genre={genre or 'N/A'} | "
            f"bpm={bpm or 'N/A'} | "
            f"beat={beat_intensity or 'N/A'}"
        )

    while True:
        choice = input("\nChoisis un numéro : ")

        try:
            selected_index = int(choice)
            if 1 <= selected_index <= len(results):
                return results[selected_index - 1]
        except ValueError:
            pass

        print("Choix invalide.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Titre ou artiste à rechercher")
    args = parser.parse_args()

    results = search_tracks(args.query)
    selected_track = choose_track(results)

    track_id = selected_track[0]
    track_bpm = selected_track[5]
    options = ask_flow_options(track_bpm)
    command = build_matching_command(track_id, options)

    print("\nCommande lancée :")
    print(" ".join(command))

    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
