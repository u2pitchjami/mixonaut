"""
2025-08-19 décorateur de scripts main.
"""

import sys
import traceback
from functools import wraps


def safe_main(func):
    """
    Décorateur pour main en catchant toutes les exceptions et retourner un code retour.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Erreur capturée par safe_main: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)  # log complet pour CronHub
            sys.exit(1)
        sys.exit(0)

    return wrapper
