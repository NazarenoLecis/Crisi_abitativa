import argparse
from pathlib import Path
import sys

RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.mappe_comunali_italia import crea_mappe_comunali_tutte_regioni


parser = argparse.ArgumentParser(
    description="Genera mappe regionali a livello comunale usando OMI, ISTAT e redditi MEF."
)
parser.add_argument("--output", default="outputs/charts", help="Cartella dove salvare i PNG.")
parser.add_argument(
    "--regione",
    default="tutte",
    help="Nome o codice ISTAT della regione da mappare. Usa 'tutte' per l'intera Italia. Default: tutte.",
)
parser.add_argument(
    "--tutte-regioni",
    action="store_true",
    help="Alias di --regione tutte. Operazione lunga.",
)
parser.add_argument(
    "--lavoratori-omi",
    type=int,
    default=4,
    help="Numero massimo di richieste OMI parallele per comune.",
)
parser.add_argument(
    "--limite-comuni",
    type=int,
    default=None,
    help="Limita il numero di comuni scaricati. Utile solo per test tecnici.",
)
parser.add_argument(
    "--pausa",
    type=float,
    default=0.0,
    help="Pausa in secondi tra i comuni, utile se l'API OMI risponde lentamente.",
)
args = parser.parse_args()

if args.tutte_regioni:
    args.regione = "tutte"

print(f"Creo mappe comunali per: {args.regione}.", flush=True)
print("Scarico OMI comune per comune: questa fase puo' richiedere tempo.", flush=True)
percorsi = crea_mappe_comunali_tutte_regioni(
    cartella_output=args.output,
    regione=args.regione,
    mostra_progresso=True,
    lavoratori_omi=args.lavoratori_omi,
    limite_comuni=args.limite_comuni,
    pausa=args.pausa,
)

print("Mappe comunali create:")
for percorso in percorsi:
    print(f"- {percorso}")
