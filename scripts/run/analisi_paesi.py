import argparse
from pathlib import Path
import sys


RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.api import scarica_ocse
from scripts.helpers.utils import stampa_ultimi_valori


parser = argparse.ArgumentParser(description="Confronta paesi OCSE scelti usando direttamente le API OECD.")
parser.add_argument("--paesi", nargs="+", default=["ITA", "DEU", "FRA", "ESP"], help="Codici ISO3 OCSE, es. ITA DEU FRA ESP")
parser.add_argument("--righe", type=int, default=80, help="Numero massimo di righe da mostrare.")
args = parser.parse_args()

dati = scarica_ocse(args.paesi)
ultimi = stampa_ultimi_valori(dati)

print("Confronto paesi OCSE")
print("Fonte: OECD SDMX API")
print(f"Paesi richiesti: {', '.join(args.paesi)}")
print(f"Righe scaricate: {len(dati):,}")
print()
print(ultimi.head(args.righe).to_string(index=False))
