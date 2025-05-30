import subprocess
from beets_utils.commands import run_beet_command  # ou où tu l’as placée


def update_beets_fields(track_path: str, field_values: dict, logname="Mixonaut", dry_run=False):
    """
    Construit et exécute une commande `beet modify` pour mettre à jour plusieurs champs.

    Args:
        track_path (str): Chemin complet du fichier à modifier
        field_values (dict): Champs à modifier (ex: {"mood": "calm", "energy_level": "high"})
        logname (str): Pour la journalisation
        dry_run (bool): Simulation sans exécution réelle
    """
    track_path = track_path.decode("utf-8") if isinstance(track_path, bytes) else track_path

    # Transforme les champs en liste de type "key=value"
    args = ["-y"]  # Ajout ici pour forcer la modification sans confirmation
    args += [f"{key}={value}" for key, value in field_values.items()]
    args += ["--nomove"]
    args.append(track_path)

    print(f"track_path : {track_path}")
    #print(f"field_values : {field_values}")
    print(f"args : {args}")

    if "bpm" in field_values:
        try:
            field_values["bpm"] = int(float(field_values["bpm"]))
            print(f"field_values['bpm'] : {type(field_values['bpm'])}")
        except (TypeError, ValueError):
            logger.warning(f"⚠️ BPM invalide : {field_values['bpm']}")
            del field_values["bpm"]


    return run_beet_command(
        command="modify",
        args=args,
        capture_output=True,
        check=True,
        dry_run=dry_run,
        logname=logname
    )
