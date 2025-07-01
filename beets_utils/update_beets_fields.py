import subprocess
from utils.logger import get_logger, with_child_logger
from beets_utils.commands import run_beet_command  # ou où tu l’as placée

@with_child_logger
def update_beets_fields(track_path: str, field_values: dict, logger=None, dry_run=False):
    """
    Construit et exécute une commande `beet modify` pour mettre à jour plusieurs champs.

    Args:
        track_path (str): Chemin complet du fichier à modifier
        field_values (dict): Champs à modifier (ex: {"mood": "calm", "energy_level": "high"})
        logger (str): Pour la journalisation
        dry_run (bool): Simulation sans exécution réelle
    """
    track_path = track_path.decode("utf-8") if isinstance(track_path, bytes) else track_path
    
    # Transforme les champs en liste de type "key=value"
    args = ["-y"]  # Ajout ici pour forcer la modification sans confirmation
    args += [f"{key}={value}" for key, value in field_values.items()]
    args += ["--nomove"]
    args.append(track_path)

    return run_beet_command(
        command="modify",
        args=args,
        capture_output=True,
        check=True,
        dry_run=dry_run,
        logger=logger
    )

def update_beets_field(track_path: str, field: str, value: str, **kwargs):
    return update_beets_fields(track_path, {field: value}, **kwargs)
