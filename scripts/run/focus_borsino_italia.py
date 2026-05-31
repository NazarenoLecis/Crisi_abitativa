import argparse
from scripts.helpers.borsino import (
    BORSINO_API_KEY_ENV,
    BORSINO_TIPO_ABITAZIONI_CIVILI,
    crea_grafici_borsino_italia,
)


parser = argparse.ArgumentParser(
    description="Genera il focus locale italiano usando Borsino Immobiliare/BorsinoPro, ISTAT e redditi MEF."
)
parser.add_argument("--output", default="outputs/charts", help="Cartella dove salvare i PNG.")
parser.add_argument(
    "--versione",
    default="capoluoghi-regione",
    choices=["tutte", "capoluoghi-regione", "regioni", "province"],
    help="Versione del focus Borsino da generare. Province richiede molte piu' chiamate API.",
)
parser.add_argument(
    "--tipo-immobile",
    type=int,
    default=BORSINO_TIPO_ABITAZIONI_CIVILI,
    help="Codice tipo immobile Borsino. Default: 20, abitazioni in stabili civili.",
)
parser.add_argument(
    "--api-key",
    default=None,
    help=f"Chiave API Borsino. In alternativa usa la variabile ambiente {BORSINO_API_KEY_ENV}.",
)
parser.add_argument(
    "--pausa",
    type=float,
    default=0.2,
    help="Pausa in secondi tra le citta', utile per non stressare l'API.",
)
args = parser.parse_args()

print("Creo il focus locale Borsino Italia.", flush=True)
print(
    "Uso Borsino come sezione aggiuntiva: non sostituisce OMI e richiede una chiave API.",
    flush=True,
)
try:
    percorsi = crea_grafici_borsino_italia(
        args.output,
        mostra_progresso=True,
        versione=args.versione,
        tipo_immobile=args.tipo_immobile,
        api_key=args.api_key,
        pausa=args.pausa,
    )
except RuntimeError as errore:
    print(str(errore), flush=True)
    raise SystemExit(1)

print("Grafici Borsino creati:")
for percorso in percorsi:
    print(f"- {percorso}")
