import argparse
from pathlib import Path
import sys


RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.mappe_focus_europa import crea_mappe_e_focus_europa


parser = argparse.ArgumentParser(description="Genera mappe e focus locali per Francia e Germania.")
parser.add_argument("--output", default="outputs", help="Cartella dove salvare PNG e CSV per paese.")
parser.add_argument(
    "--paesi",
    nargs="+",
    default=["FRA", "DEU"],
    choices=["FRA", "DEU"],
    help="Paesi da generare. Default: FRA DEU.",
)
args = parser.parse_args()

percorsi = crea_mappe_e_focus_europa(args.output, paesi=args.paesi, mostra_progresso=True)
print("Grafici creati:")
for percorso in percorsi:
    print(f"- {percorso}")
