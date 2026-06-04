from pathlib import Path
import sys


RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.api import scarica_ocse


RIGHE = 20


def run(righe=RIGHE):
    """
    Stampa a terminale la copertura degli indicatori OECD scaricabili.

    Valori utili:
    - righe: numero di righe di esempio da mostrare.
    """
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
    print(dati.head(righe).to_string(index=False))
    return dati


if __name__ == "__main__":
    run(righe=RIGHE)
