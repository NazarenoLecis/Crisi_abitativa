import argparse
from api import scarica_ocse
from utils import stampa_ultimi_valori


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
