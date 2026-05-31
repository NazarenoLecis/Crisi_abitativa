import argparse
from scripts.helpers.api import scarica_ocse


parser = argparse.ArgumentParser(description="Estrae via API gli indicatori abitativi OCSE disponibili.")
parser.add_argument("--righe", type=int, default=20, help="Numero di righe da mostrare a terminale.")
args = parser.parse_args()

dati = scarica_ocse()

print(f"Righe scaricate: {len(dati):,}")
print(f"Paesi disponibili: {dati['country_code'].nunique()}")
print(f"Indicatori disponibili: {dati['indicator_id'].nunique()}")
print()
print("Copertura per indicatore:")
copertura = dati.groupby("indicator_name").agg(paesi=("country_code", "nunique"), osservazioni=("value", "size"))
print(copertura.sort_values("paesi", ascending=False).to_string())
print()
print("Prime righe:")
print(dati.head(args.righe).to_string(index=False))
