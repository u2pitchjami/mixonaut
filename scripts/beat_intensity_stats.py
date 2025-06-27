from db.access import select_all
from utils.logger import get_logger
import statistics

logname = "beat_intensity_stats"
logger = get_logger(logname)

FIELDS = [
    "spectral_flux", "spectral_rms_mean", "average_loudness",
    "spectral_energy", "dynamic_complexity", "onset_rate",
    "beats_loudness_mean"
]


def fetch_values():
    cols = ", ".join(FIELDS)
    query = f"SELECT {cols} FROM audio_features"
    return select_all(query, logname=logname)


def compute_stats():
    rows = fetch_values()
    if not rows:
        logger.warning("Aucune donnée trouvée.")
        return

    transposed = list(zip(*rows))
    print("\n--- Statistiques des champs d'intensité ---")
    for i, field in enumerate(FIELDS):
        values = [v for v in transposed[i] if v is not None]
        if not values:
            print(f"{field}: (aucune valeur valide)")
            continue
        print(f"{field:<20} → min: {min(values):.3f}, max: {max(values):.3f}, mean: {statistics.mean(values):.3f}, stdev: {statistics.stdev(values):.3f}")


if __name__ == "__main__":
    compute_stats()