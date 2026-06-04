from pathlib import Path
import sys


RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.mappe_focus_europa import crea_mappe_e_focus_europa


OUTPUT = "outputs"
PAESI = ["FRA", "DEU"]


def run(output=OUTPUT, paesi=PAESI):
    """
    Genera mappe e focus locali per Francia e Germania.

    Valori accettati per `paesi`:
    - "FRA";
    - "DEU";
    - ["FRA", "DEU"].
    """
    percorsi = crea_mappe_e_focus_europa(output, paesi=paesi, mostra_progresso=True)
    print("Grafici creati:")
    for percorso in percorsi:
        print(f"- {percorso}")
    return percorsi


if __name__ == "__main__":
    run(output=OUTPUT, paesi=PAESI)
