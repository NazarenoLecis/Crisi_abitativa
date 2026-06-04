from pathlib import Path
import sys

RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.affitti_brevi import crea_affitti_brevi_italia


OUTPUT = "outputs"
REGIONE = "tutte"
PROFILO = "residenziale"


def run(output=OUTPUT, regione=REGIONE, profilo=PROFILO):
    """
    Genera CSV, classifiche e mappe comunali sugli affitti brevi dal registro CIN.

    Valori accettati:
    - regione: "tutte" oppure nome regione, es. "Sardegna", "Lombardia";
    - profilo: "residenziale", "privati", "c2", "totale".
    """
    print("Creo la sezione affitti brevi.", flush=True)
    print("Scarico e preparo i dati: se usi tutte le regioni la fase mappe puo' richiedere qualche minuto.", flush=True)
    percorsi = crea_affitti_brevi_italia(
        cartella_output=output,
        regione=regione,
        profilo=profilo,
        mostra_progresso=True,
    )

    print("Sezione affitti brevi completata:")
    for percorso in percorsi:
        print(f"- {percorso}")
    return percorsi


if __name__ == "__main__":
    run(output=OUTPUT, regione=REGIONE, profilo=PROFILO)
