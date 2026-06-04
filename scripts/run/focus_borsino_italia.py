from pathlib import Path
import sys


RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.borsino import BORSINO_TIPO_ABITAZIONI_CIVILI, crea_grafici_borsino_italia


OUTPUT = "outputs"
VERSIONE = "capoluoghi-regione"
TIPO_IMMOBILE = BORSINO_TIPO_ABITAZIONI_CIVILI
API_KEY = None
PAUSA = 0.2


def run(output=OUTPUT, versione=VERSIONE, tipo_immobile=TIPO_IMMOBILE, api_key=API_KEY, pausa=PAUSA):
    """
    Genera il focus locale italiano usando Borsino Immobiliare/BorsinoPro.

    Valori accettati per `versione`:
    - "tutte";
    - "capoluoghi-regione";
    - "regioni";
    - "province".

    Questo script genera solo Borsino: qui serve una chiave API Borsino.
    Puoi passarla con `api_key` oppure impostare la variabile ambiente
    BORSINO_API_KEY.

    Nel runner principale `scripts/run/genera_grafici.py`, invece, gli
    argomenti Borsino sono facoltativi finche' `includi_borsino=False`.
    """
    print("Creo il focus locale Borsino Italia.", flush=True)
    print("Uso Borsino come sezione aggiuntiva: non sostituisce OMI e richiede una chiave API.", flush=True)
    try:
        percorsi = crea_grafici_borsino_italia(
            output,
            mostra_progresso=True,
            versione=versione,
            tipo_immobile=tipo_immobile,
            api_key=api_key,
            pausa=pausa,
        )
    except RuntimeError as errore:
        print(str(errore), flush=True)
        raise SystemExit(1)

    print("Grafici Borsino creati:")
    for percorso in percorsi:
        print(f"- {percorso}")
    return percorsi


if __name__ == "__main__":
    run(output=OUTPUT, versione=VERSIONE, tipo_immobile=TIPO_IMMOBILE, api_key=API_KEY, pausa=PAUSA)
