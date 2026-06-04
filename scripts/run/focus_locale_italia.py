from pathlib import Path
import sys


RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.grafici_locali_italia import crea_grafici_locali_italia


OUTPUT = "outputs"
VERSIONE = "tutte"
LAVORATORI_OMI = 4


def run(output=OUTPUT, versione=VERSIONE, lavoratori_omi=LAVORATORI_OMI):
    """
    Genera il focus locale italiano usando OMI, ISTAT e redditi MEF.

    Valori accettati per `versione`:
    - "tutte";
    - "capoluoghi-regione";
    - "regioni";
    - "province".
    """
    print("Creo il focus locale italiano.", flush=True)
    percorsi = crea_grafici_locali_italia(
        output,
        mostra_progresso=True,
        versione=versione,
        lavoratori_omi=lavoratori_omi,
    )

    print("Grafici focus locale creati:")
    for percorso in percorsi:
        print(f"- {percorso}")
    return percorsi


if __name__ == "__main__":
    run(output=OUTPUT, versione=VERSIONE, lavoratori_omi=LAVORATORI_OMI)
