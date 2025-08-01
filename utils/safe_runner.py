import sys
import traceback
from functools import wraps

def safe_main(func):
    """
    Décorateur pour exécuter un main en catchant toutes les exceptions
    et retourner un code retour adapté pour CronHub.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            print("pouet")
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Erreur capturée par safe_main: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)  # log complet pour CronHub
            sys.exit(1)
        sys.exit(0)
    return wrapper
