import argparse
from pathlib import Path
import sys


RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.grafici_locali_italia import crea_grafici_locali_italia


parser = argparse.ArgumentParser(description="Genera il focus locale italiano usando OMI, ISTAT e redditi MEF.")
parser.add_argument("--output", default="outputs", help="Cartella dove salvare PNG e CSV per paese.")
parser.add_argument(
    "--versione",
    default="tutte",
    choices=["tutte", "capoluoghi-regione", "regioni", "province"],
    help="Versione del focus locale da generare.",
)
parser.add_argument(
    "--lavoratori-omi",
    type=int,
    default=4,
    help="Numero massimo di richieste OMI parallele per comune.",
)
args = parser.parse_args()

print("Creo il focus locale italiano.", flush=True)
percorsi = crea_grafici_locali_italia(
    args.output,
    mostra_progresso=True,
    versione=args.versione,
    lavoratori_omi=args.lavoratori_omi,
)

print("Grafici focus locale creati:")
for percorso in percorsi:
    print(f"- {percorso}")
