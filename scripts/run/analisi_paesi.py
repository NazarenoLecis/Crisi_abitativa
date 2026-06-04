from pathlib import Path
import sys


RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.api import scarica_ocse
from scripts.helpers.paesi import valori_paesi
from scripts.helpers.utils import stampa_ultimi_valori


PAESI = ["ITA", "DEU", "FRA", "ESP"]
RIGHE = 80


def run(paesi=PAESI, righe=RIGHE):
    """
    Stampa a terminale gli ultimi valori OECD per alcuni paesi.

    Valori utili per `paesi`:
    - "ITA" per un paese singolo;
    - ["ITA", "DEU", "FRA", "ESP"] per una lista di paesi OECD.
    """
    paesi_richiesti = valori_paesi(paesi)
    dati = scarica_ocse(paesi_richiesti)
    ultimi = stampa_ultimi_valori(dati)

    print("Confronto paesi OCSE")
    print("Fonte: OECD SDMX API")
    print(f"Paesi richiesti: {', '.join(paesi_richiesti)}")
    print(f"Righe scaricate: {len(dati):,}")
    print()
    print(ultimi.head(righe).to_string(index=False))
    return dati


if __name__ == "__main__":
    run(paesi=PAESI, righe=RIGHE)
