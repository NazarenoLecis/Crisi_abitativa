import argparse
from pathlib import Path
import sys

RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.affitti_brevi import PROFILI_AFFITTI_BREVI, crea_affitti_brevi_italia


parser = argparse.ArgumentParser(
    description="Genera CSV, classifiche e mappe comunali sugli affitti brevi dal registro CIN."
)
parser.add_argument("--output", default="outputs", help="Cartella dove salvare PNG e CSV per paese.")
parser.add_argument(
    "--regione",
    default="tutte",
    help="Nome o codice ISTAT della regione da mappare. Usa 'tutte' per l'intera Italia. Default: tutte.",
)
parser.add_argument(
    "--profilo",
    default="residenziale",
    choices=sorted(PROFILI_AFFITTI_BREVI),
    help="Filtro del registro CIN da usare. Default: residenziale.",
)
args = parser.parse_args()

print("Creo la sezione affitti brevi.", flush=True)
print("Scarico e preparo i dati: se usi tutte le regioni la fase mappe puo' richiedere qualche minuto.", flush=True)
percorsi = crea_affitti_brevi_italia(
    cartella_output=args.output,
    regione=args.regione,
    profilo=args.profilo,
    mostra_progresso=True,
)

print("Sezione affitti brevi completata:")
for percorso in percorsi:
    print(f"- {percorso}")
