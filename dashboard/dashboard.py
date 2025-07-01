from pathlib import Path
import sys
from db.access import execute_query
from utils.config import QUERIES_DIR
from rich import print

def list_queries():
    return {f.stem: f for f in Path(QUERIES_DIR).glob("*.sql")}

def execute_sql_file(path):
    """Découpe et exécute toutes les requêtes d’un fichier .sql"""
    print(f"\n[bold cyan]📄 {path.name}[/bold cyan]")
    sql_text = path.read_text(encoding="utf-8")
    blocks = [q.strip() for q in sql_text.split(';') if q.strip()]
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

def run_query(name):
    queries = list_queries()
    if name not in queries:
        print(f"[red]❌ Requête inconnue : {name}[/red]")
        return
    execute_sql_file(queries[name])

def run_all_queries():
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