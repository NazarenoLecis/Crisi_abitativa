from pathlib import Path
import sys

RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.mappe_comunali_italia import crea_mappe_comunali_tutte_regioni


OUTPUT = "outputs"
REGIONE = "tutte"
LAVORATORI_OMI = 4
LIMITE_COMUNI = None
PAUSA = 0.0


def run(
    output=OUTPUT,
    regione=REGIONE,
    lavoratori_omi=LAVORATORI_OMI,
    limite_comuni=LIMITE_COMUNI,
    pausa=PAUSA,
):
    """
    Genera mappe regionali a livello comunale usando OMI, ISTAT e redditi MEF.

    Valori utili:
    - regione: "tutte" oppure nome regione, es. "Sardegna", "Lombardia";
    - limite_comuni: None per tutti i comuni, oppure un numero per test tecnici;
    - pausa: secondi di pausa tra richieste OMI, es. 0.2 se l'API e' lenta.
    """
    print(f"Creo mappe comunali per: {regione}.", flush=True)
    print("Scarico OMI comune per comune: questa fase puo' richiedere tempo.", flush=True)
    percorsi = crea_mappe_comunali_tutte_regioni(
        cartella_output=output,
        regione=regione,
        mostra_progresso=True,
        lavoratori_omi=lavoratori_omi,
        limite_comuni=limite_comuni,
        pausa=pausa,
    )

    print("Mappe comunali create:")
    for percorso in percorsi:
        print(f"- {percorso}")
    return percorsi


if __name__ == "__main__":
    run(
        output=OUTPUT,
        regione=REGIONE,
        lavoratori_omi=LAVORATORI_OMI,
        limite_comuni=LIMITE_COMUNI,
        pausa=PAUSA,
    )
