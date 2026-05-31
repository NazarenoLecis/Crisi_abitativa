import argparse
from scripts.helpers.api import scarica_tutto
from scripts.helpers.grafici import crea_grafici
from scripts.helpers.grafici_europei import crea_grafici_europei
from scripts.helpers.grafici_locali_italia import crea_grafici_locali_italia
from scripts.helpers.grafici_oecd import crea_grafici_oecd
from scripts.helpers.grafici_oecd_affordable import crea_grafici_oecd_affordable
from scripts.helpers.borsino import BORSINO_TIPO_ABITAZIONI_CIVILI, crea_grafici_borsino_italia


parser = argparse.ArgumentParser(description="Genera grafici usando direttamente le API Eurostat e OECD.")
parser.add_argument("--output", default="outputs/charts", help="Cartella dove salvare i PNG.")
parser.add_argument(
    "--includi-borsino",
    action="store_true",
    help="Include la sezione aggiuntiva Borsino. Richiede BORSINO_API_KEY o --api-key-borsino.",
)
parser.add_argument(
    "--versione-borsino",
    default="capoluoghi-regione",
    choices=["tutte", "capoluoghi-regione", "regioni", "province"],
    help="Versione Borsino da generare se --includi-borsino e' attivo.",
)
parser.add_argument(
    "--tipo-immobile-borsino",
    type=int,
    default=BORSINO_TIPO_ABITAZIONI_CIVILI,
    help="Codice tipo immobile Borsino. Default: 20, abitazioni in stabili civili.",
)
parser.add_argument("--api-key-borsino", default=None, help="Chiave API Borsino opzionale.")
parser.add_argument(
    "--pausa-borsino",
    type=float,
    default=0.2,
    help="Pausa in secondi tra le citta' per la sezione Borsino.",
)
args = parser.parse_args()

print("Avvio generazione grafici crisi abitativa.", flush=True)
print("Scarico i dati dalle API: questa fase puo' richiedere qualche minuto.", flush=True)
dati = scarica_tutto(mostra_progresso=True)

print("Dati pronti. Inizio a creare e salvare i grafici.", flush=True)
percorsi = crea_grafici(dati, args.output, mostra_progresso=True)

print("Creo i confronti Italia-UE sui principali indicatori abitativi.", flush=True)
percorsi.extend(crea_grafici_europei(args.output, mostra_progresso=True))

print("Creo i confronti OECD sui prezzi delle case.", flush=True)
percorsi.extend(crea_grafici_oecd(args.output, mostra_progresso=True))

print("Creo i grafici dalla OECD Affordable Housing Database.", flush=True)
percorsi.extend(crea_grafici_oecd_affordable(args.output, mostra_progresso=True))

print("Creo il focus locale sui capoluoghi italiani.", flush=True)
percorsi.extend(crea_grafici_locali_italia(args.output, mostra_progresso=True))

if args.includi_borsino:
    print("Creo la sezione aggiuntiva Borsino.", flush=True)
    try:
        percorsi.extend(
            crea_grafici_borsino_italia(
                args.output,
                mostra_progresso=True,
                versione=args.versione_borsino,
                tipo_immobile=args.tipo_immobile_borsino,
                api_key=args.api_key_borsino,
                pausa=args.pausa_borsino,
            )
        )
    except RuntimeError as errore:
        print(str(errore), flush=True)
        raise SystemExit(1)

print("Grafici creati:")
for percorso in percorsi:
    print(f"- {percorso}")
