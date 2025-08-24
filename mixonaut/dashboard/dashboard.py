"""
2025-08-20.

dashboard de contrôle
"""

import sys
from pathlib import Path

from rich import print

from mixonaut.db.access import execute_query
from mixonaut.utils.config import QUERIES_DIR

ALIASES = {
    "ready_for_deletion": "SELECT * FROM v_ready_for_deletion ORDER BY age_days DESC, ratio DESC;",
    "needs_manual": "SELECT * FROM v_needs_manual ORDER BY since_decision_days \
        DESC NULLS LAST, age_days DESC, torrent_name;",
    "rejected": "SELECT * FROM v_rejected ORDER BY age_days DESC, torrent_name;",
}


def list_queries() -> dict[str, Path]:
    """
    Returns a dictionary mapping query filenames to their corresponding SQL queries.

    The queries are stored in the `QUERIES_DIR` directory.
    """
    return {f.stem: f for f in Path(QUERIES_DIR).glob("*.sql")}


def execute_sql_file(path: Path) -> None:
    """
    Découpe et exécute toutes les requêtes d’un fichier .sql.
    """
    print(f"\n[bold cyan]📄 {path.name}[/bold cyan]")
    sql_text = path.read_text(encoding="utf-8")
    blocks = [q.strip() for q in sql_text.split(";") if q.strip()]
    for sql in blocks:
        try:
            print(f"\n[green]➤ Requête :[/green] [dim]{sql[:80]}[/dim]...")
            result = execute_query(sql, fetch=True)
            if result:
                for row in result:
                    print(row)
            else:
                print("[yellow]↪️ Aucun résultat[/yellow]")
        except Exception as e:
            print(f"[red]❌ Erreur : {e}[/red]")


def run_query(name: str) -> None:
    """
    Execute a query based on the provided name.

    The function checks if the provided `name` is an alias. If it is, the corresponding SQL query
    from the `ALIASES` dictionary is executed and the results are printed. If the `name` is not an
    alias, the function prints a message indicating that no action will be taken.
    Args:
        name (str): The name of the query to execute or the alias for which to retrieve the SQL query.
    """
    queries = list_queries()
    if name in ALIASES:
        sql = ALIASES[name]
        print(f"\n[bold cyan]📄 Alias : {name}[/bold cyan]")
        try:
            result = execute_query(sql, fetch=True)
            if result:
                for row in result:
                    print(row)
            else:
                print("[yellow]↪️ Aucun résultat[/yellow]")
        except Exception as e:
            print(f"[red]❌ Erreur : {e}[/red]")
        return

    if name not in queries:
        print(f"[red]❌ Requête inconnue : {name}[/red]")
        return
    execute_sql_file(queries[name])


def run_all_queries() -> None:
    """
    Execute all SQL files in the `QUERIES_DIR` directory.

    This function iterates over the dictionary returned by `list_queries()` and executes each SQL file using
    `execute_sql_file()`.
    """
    queries = list_queries()
    print(f"[blue]📊 Exécution de toutes les requêtes dans {QUERIES_DIR}[/blue]")
    for name, path in sorted(queries.items()):
        execute_sql_file(path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("[cyan]Usage : python dashboard.py <nom_requete>[/cyan]")
        print("Ou : python dashboard.py --all")
        print("\n[bold]Requêtes disponibles :[/bold]")
        for name in list_queries():
            print(f"  - {name}")
        sys.exit(0)

    arg = sys.argv[1]
    if arg == "--all":
        run_all_queries()
    else:
        run_query(arg)
